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
                        // A traffic_state reports the current phase; decision_change.to_phase is only a proposal.
                        String oldPhase = stateNode.path("current_phase_id").asText("");
                        String oldMode = stateNode.path("mode").asText("");
                        String phase = root.path("current_phase_id").asText("");
                        String mode = root.path("mode").asText(oldMode.isEmpty() ? "normal" : oldMode);
                        if ("clearance".equalsIgnoreCase(mode)) {
                            if (!"clearance".equalsIgnoreCase(oldMode) || stateNode.path("clearing_phase").asText("").isEmpty()) {
                                stateNode.put("clearing_phase", oldPhase.isEmpty() ? phase : oldPhase);
                            }
                        } else {
                            stateNode.remove("clearing_phase");
                        }
                        stateNode.put("current_phase_id", phase);
                        stateNode.put("mode", mode);
                        if (root.has("degradation")) stateNode.set("degradation", root.get("degradation"));
                        if (root.has("lanes")) stateNode.set("lanes", root.get("lanes"));
                    } else if ("mode_change".equals(subType)) {
                        String mode = root.path("to_mode").asText("unknown");
                        String previous = stateNode.path("mode").asText("");
                        if ("clearance".equalsIgnoreCase(mode) && !"clearance".equalsIgnoreCase(previous)) {
                            String exiting = stateNode.path("current_phase_id").asText("");
                            if (!exiting.isEmpty()) stateNode.put("clearing_phase", exiting);
                        } else if (!"clearance".equalsIgnoreCase(mode)) {
                            // Never relight the old approach on a mode-only return to normal.
                            boolean nextAlreadyReported = "clearance".equalsIgnoreCase(previous)
                                    && stateNode.hasNonNull("clearing_phase")
                                    && !stateNode.path("current_phase_id").asText("").equals(stateNode.path("clearing_phase").asText(""));
                            if ("normal".equalsIgnoreCase(mode) && !"normal".equalsIgnoreCase(previous) && !nextAlreadyReported) {
                                stateNode.remove("current_phase_id");
                            }
                            stateNode.remove("clearing_phase");
                        }
                        stateNode.put("mode", mode);
                        if (root.has("current_phase_id")) stateNode.set("current_phase_id", root.get("current_phase_id"));
                    } else if ("degradation_change".equals(subType)) {
                        String toDegradation = root.has("to_mode") ? root.get("to_mode").asText() : "normal";
                        stateNode.put("degradation", toDegradation);
                    }
                }

                String phase = stateNode.path("clearing_phase").asText(stateNode.path("current_phase_id").asText(""));
                stateNode.set("signal_colors", objectMapper.valueToTree(SignalDisplay.colors(phase, stateNode.path("mode").asText(""))));
                // 保存至 Redis，保持 2 小时有效
                redisTemplate.opsForValue().set(stateKey, objectMapper.writeValueAsString(stateNode), Duration.ofHours(2));

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

}
