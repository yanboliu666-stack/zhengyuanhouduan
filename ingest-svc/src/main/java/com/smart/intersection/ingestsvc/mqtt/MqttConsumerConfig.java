package com.smart.intersection.ingestsvc.mqtt;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.core.MessageProducer;
import org.springframework.integration.mqtt.core.DefaultMqttPahoClientFactory;
import org.springframework.integration.mqtt.core.MqttPahoClientFactory;
import org.springframework.integration.mqtt.inbound.MqttPahoMessageDrivenChannelAdapter;
import org.springframework.integration.mqtt.support.DefaultPahoMessageConverter;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageHandler;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Configuration
public class MqttConsumerConfig {

    @Value("${mqtt.url:tcp://127.0.0.1:1883}")
    private String mqttUrl;

    @Value("${mqtt.client-id:cloud-ingest-svc}")
    private String clientId;

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public MqttConsumerConfig(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Bean
    public MqttPahoClientFactory mqttClientFactory() {
        DefaultMqttPahoClientFactory factory = new DefaultMqttPahoClientFactory();
        MqttConnectOptions options = new MqttConnectOptions();
        options.setServerURIs(new String[]{mqttUrl});
        options.setCleanSession(true);
        options.setAutomaticReconnect(true);
        options.setConnectionTimeout(10);
        options.setKeepAliveInterval(30);
        factory.setConnectionOptions(options);
        return factory;
    }

    @Bean
    public MessageChannel mqttInputChannel() {
        return new DirectChannel();
    }

    @Bean
    public MessageProducer inbound() {
        MqttPahoMessageDrivenChannelAdapter adapter =
                new MqttPahoMessageDrivenChannelAdapter(clientId + "_sub_" + System.currentTimeMillis(),
                        mqttClientFactory(),
                        "traffic-control/+/event/#",
                        "traffic-control/+/alarm");
        adapter.setCompletionTimeout(5000);
        adapter.setConverter(new DefaultPahoMessageConverter());
        adapter.setQos(1);
        adapter.setOutputChannel(mqttInputChannel());
        return adapter;
    }

    @Bean
    @ServiceActivator(inputChannel = "mqttInputChannel")
    public MessageHandler handler() {
        return message -> {
            String topic = (String) message.getHeaders().get("mqtt_receivedTopic");
            String payload = (String) message.getPayload();
            if (topic == null || payload == null) return;

            try {
                String[] parts = topic.split("/");
                String junctionId = parts.length > 1 ? parts[1] : "mini_1";
                String msgType = parts.length > 2 ? parts[2] : "";
                String subType = parts.length > 3 ? parts[3] : "";

                JsonNode root = objectMapper.readTree(payload);
                String tickId = root.has("tick_id") ? root.get("tick_id").asText() : String.valueOf(System.currentTimeMillis());

                // Redis 状态存储 Key
                String stateKey = "junction:state:" + junctionId;
                String existingStr = redisTemplate.opsForValue().get(stateKey);
                ObjectNode stateNode = existingStr != null ? (ObjectNode) objectMapper.readTree(existingStr) : objectMapper.createObjectNode();

                stateNode.put("junction_id", junctionId);
                stateNode.put("tick_id", tickId);
                stateNode.put("last_updated", System.currentTimeMillis());

                if ("alarm".equals(msgType)) {
                    log.warn("【边缘端故障告警】路口: {}, 内容: {}", junctionId, payload);
                    redisTemplate.opsForList().leftPush("junction:alarms:" + junctionId, payload);
                    redisTemplate.opsForList().trim("junction:alarms:" + junctionId, 0, 19);
                    stateNode.put("latest_alarm", root.has("alarm_type") ? root.get("alarm_type").asText() : "warning");
                } else if ("event".equals(msgType)) {
                    if ("traffic_state".equals(subType)) {
                        String currentPhase = root.has("current_phase_id") ? root.get("current_phase_id").asText() : "P_N";
                        String degradation = root.has("degradation") ? root.get("degradation").asText() : "normal";
                        stateNode.put("current_phase_id", currentPhase);
                        stateNode.put("degradation", degradation);
                        if (root.has("lanes")) {
                            stateNode.set("lanes", root.get("lanes"));
                        }

                        // 精准推算四向信号灯
                        String currentMode = stateNode.has("mode") ? stateNode.get("mode").asText() : "normal";
                        Map<String, String> colors = calculateSignalColors(currentPhase, currentMode);
                        stateNode.set("signal_colors", objectMapper.valueToTree(colors));

                    } else if ("mode_change".equals(subType)) {
                        String toMode = root.has("to_mode") ? root.get("to_mode").asText() : "normal";
                        stateNode.put("mode", toMode);
                        String currentPhase = stateNode.has("current_phase_id") ? stateNode.get("current_phase_id").asText() : "P_N";
                        stateNode.set("signal_colors", objectMapper.valueToTree(calculateSignalColors(currentPhase, toMode)));

                    } else if ("degradation_change".equals(subType)) {
                        String toDegradation = root.has("to_mode") ? root.get("to_mode").asText() : "normal";
                        stateNode.put("degradation", toDegradation);
                    }
                }

                // 保存至 Redis，保持 2 小时有效
                redisTemplate.opsForValue().set(stateKey, objectMapper.writeValueAsString(stateNode), Duration.ofHours(2));
                redisTemplate.opsForValue().set("junction:state:INT_001", objectMapper.writeValueAsString(stateNode), Duration.ofHours(2));

                log.info("【数字孪生状态同步】路口: {}, 相位: {}, 模式: {}, 降级: {}",
                        junctionId,
                        stateNode.has("current_phase_id") ? stateNode.get("current_phase_id").asText() : "-",
                        stateNode.has("mode") ? stateNode.get("mode").asText() : "-",
                        stateNode.has("degradation") ? stateNode.get("degradation").asText() : "-");

            } catch (Exception e) {
                log.error("【MQTT 数据解析异常】Payload: {}, Error: {}", payload, e.getMessage());
            }
        };
    }

    /**
     * 四向红绿灯核心解算规则：
     * P_N / P_S: 南北方向绿灯通行，东西方向红灯禁行
     * P_E / P_W: 东西方向绿灯通行，南北方向红灯禁行
     * clearance: 四向全部黄灯清空
     * all_red:   四向全部红灯
     */
    private Map<String, String> calculateSignalColors(String phaseId, String mode) {
        Map<String, String> colors = new HashMap<>();

        if ("all_red".equalsIgnoreCase(mode)) {
            colors.put("north", "red");
            colors.put("south", "red");
            colors.put("east", "red");
            colors.put("west", "red");
            return colors;
        }

        if ("clearance".equalsIgnoreCase(mode)) {
            colors.put("north", "yellow");
            colors.put("south", "yellow");
            colors.put("east", "yellow");
            colors.put("west", "yellow");
            return colors;
        }

        // 默认状态：全红
        colors.put("north", "red");
        colors.put("south", "red");
        colors.put("east", "red");
        colors.put("west", "red");

        String p = phaseId.toUpperCase();
        if (p.contains("N") || p.contains("S") || "0".equals(p) || "1".equals(p) || "P_1".equals(p) || "P_2".equals(p)) {
            // 南北放行
            colors.put("north", "green");
            colors.put("south", "green");
            colors.put("east", "red");
            colors.put("west", "red");
        } else if (p.contains("E") || p.contains("W") || "2".equals(p) || "3".equals(p) || "P_3".equals(p) || "P_4".equals(p)) {
            // 东西放行
            colors.put("east", "green");
            colors.put("west", "green");
            colors.put("north", "red");
            colors.put("south", "red");
        }

        // 兼容原有的 _through 命名
        colors.put("north_through", colors.get("north"));
        colors.put("south_through", colors.get("south"));
        colors.put("east_through", colors.get("east"));
        colors.put("west_through", colors.get("west"));

        return colors;
    }
}