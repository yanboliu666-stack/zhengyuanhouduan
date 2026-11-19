package com.smart.intersection.ingestsvc.mqtt;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageHandler;
import org.springframework.messaging.MessagingException;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Component
public class MqttEventConsumer implements MessageHandler {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public void handleMessage(Message<?> message) throws MessagingException {
        try {
            String topic = message.getHeaders().get("mqtt_receivedTopic", String.class);
            String payload = message.getPayload().toString();

            JsonNode json = objectMapper.readTree(payload);

            // 提取契约核心字段
            String junctionId = json.has("junction_id") ? json.get("junction_id").asText() : "INT_001";
            long tickId = json.has("tick_id") ? json.get("tick_id").asLong() : 0L;
            String eventType = extractEventType(topic);

            // 契约第 5 节：幂等去重 (junction_id, event_type, tick_id)
            String dedupKey = String.format("event_dedup:%s:%s:%d", junctionId, eventType, tickId);
            Boolean isNewEvent = redisTemplate.opsForValue().setIfAbsent(dedupKey, "1", Duration.ofHours(24));

            if (Boolean.FALSE.equals(isNewEvent)) {
                // 重复事件，直接忽略
                return;
            }

            // 处理逻辑：缓存路口最新状态到 Redis 供前端大屏实时拉取
            if ("decision_change".equals(eventType) || "mode_change".equals(eventType)) {
                redisTemplate.opsForValue().set("junction:state:" + junctionId, payload);
            }

            // 如果是告警，写入 Redis 告警队列供 alert-svc 消费
            if ("alarm".equals(eventType) || "feedback_failure".equals(eventType) || "heartbeat_fault".equals(eventType)) {
                redisTemplate.opsForList().leftPush("queue:alarms", payload);
            }

        } catch (Exception e) {
            // 契约第 6 节：尽力而为原则，日志层/消费层报错决不影响主链路
            e.printStackTrace();
        }
    }

    private String extractEventType(String topic) {
        if (topic == null) return "unknown";
        String[] parts = topic.split("/");
        return parts[parts.length - 1];
    }
}