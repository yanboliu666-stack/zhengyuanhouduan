package com.smart.intersection.dispatch.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smart.intersection.dispatch.dto.DispatchReqDTO;
import com.smart.intersection.dispatch.entity.DispatchLogEntity;
import com.smart.intersection.dispatch.repository.DispatchLogRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class DispatchService {

    @Autowired
    private DispatchLogRepository dispatchLogRepository;

    @Autowired
    private ObjectMapper objectMapper;

    /**
     * 下发 MQTT 信号配时/控制指令并记录日志
     */
    public DispatchLogEntity sendDispatchCommand(DispatchReqDTO req) {
        // 1. 基础参数解析与兜底
        String intersectionId = (req != null && req.getIntersectionId() != null && !req.getIntersectionId().trim().isEmpty())
                ? req.getIntersectionId() : "INT_001";

        String commandType = (req != null && req.getCommandType() != null && !req.getCommandType().trim().isEmpty())
                ? req.getCommandType() : "SIGNAL_TIMING";

        // 2. 构造符合《运行日志数据契约》规范的 MQTT Payload 字典
        Map<String, Object> mqttPayloadMap = new HashMap<>();
        mqttPayloadMap.put("junction_id", intersectionId);
        mqttPayloadMap.put("command_type", commandType);
        mqttPayloadMap.put("ts_wall", System.currentTimeMillis() / 1000.0); // 秒级挂钟时间戳

        // 如果包含配时参数，填充配时数据
        if (req != null) {
            if (req.getCycleLength() != null) {
                mqttPayloadMap.put("cycle_length", req.getCycleLength());
            }
            if (req.getGreenTimes() != null && !req.getGreenTimes().isEmpty()) {
                mqttPayloadMap.put("green_times", req.getGreenTimes());
            }
            if (req.getPayload() != null) {
                mqttPayloadMap.put("extra_payload", req.getPayload());
            }
        }

        // 3. 序列化 Payload 为 JSON 字符串
        String payloadJson;
        try {
            payloadJson = objectMapper.writeValueAsString(mqttPayloadMap);
        } catch (Exception e) {
            log.error("下发指令 JSON 序列化失败, 使用默认格式", e);
            payloadJson = String.format("{\"junction_id\":\"%s\",\"command_type\":\"%s\"}", intersectionId, commandType);
        }

        // 4. 模拟/触发 MQTT 消息下发
        // 对应契约 Topic 规范: traffic-control/{junction_id}/command
        String mqttTopic = String.format("traffic-control/%s/command", intersectionId);
        log.info("【MQTT 指令下发】Topic: {}, Payload: {}", mqttTopic, payloadJson);

        // 5. 构造并保存下发日志实体（尽力而为落库）
        DispatchLogEntity logEntity = DispatchLogEntity.builder()
                .intersectionId(intersectionId)
                .commandType(commandType)
                .payload(payloadJson)
                .status("SUCCESS")
                .message("MQTT 指令已成功发布至边缘网关")
                .createTime(LocalDateTime.now())
                .build();

        return dispatchLogRepository.save(logEntity);
    }
}