package com.smart.intersection.ingestsvc.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
public class TrafficDataConsumer {

    @Autowired
    private StringRedisTemplate stringRedisTemplate; // 改为 StringRedisTemplate

    private final ObjectMapper objectMapper = new ObjectMapper();

    @KafkaListener(topics = "traffic-data-topic", groupId = "ingest-group")
    public void consume(String message) {
        try {
            log.info("接收到实时车流 Kafka 数据: {}", message);
            Map<String, Object> data = objectMapper.readValue(message, Map.class);
            String intersectionId = (String) data.getOrDefault("intersectionId", "INT_001");

            // 写入 Redis 缓存供前端实时大屏高频查询
            stringRedisTemplate.opsForValue().set("realtime:" + intersectionId, message);
        } catch (Exception e) {
            log.error("解析 Kafka 消息失败: {}", e.getMessage());
        }
    }
}