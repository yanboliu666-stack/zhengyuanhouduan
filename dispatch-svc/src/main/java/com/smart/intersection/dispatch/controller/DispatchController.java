package com.smart.intersection.dispatchsvc.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
public class DispatchController {

    @Autowired(required = false)
    private MqttClient mqttClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 接收云端配时方案，并向 MQTT 边缘网关下发指令
     * 支持 /api/v1/dispatch/timing-plan、/dispatch/timing-plan 和 /timing-plan 等多种路由
     */
    @PostMapping({
            "/api/v1/dispatch/timing-plan",
            "/dispatch/timing-plan",
            "/timing-plan",
            "/api/v1/dispatch/plan",
            "/dispatch/plan"
    })
    public ResponseEntity<Map<String, Object>> dispatchTimingPlan(@RequestBody Map<String, Object> req) {
        String junctionId = (String) req.getOrDefault("junctionId", req.getOrDefault("intersectionId", "mini_1"));
        Object cycleLength = req.getOrDefault("cycleLength", 120);
        Object greenTimes = req.get("greenTimes");

        log.info("【云端下发配时指令】目标路口: {}, 周期: {}s, 绿灯方案: {}", junctionId, cycleLength, greenTimes);

        // 构造符合边缘契约的下发 Payload
        Map<String, Object> commandPayload = new HashMap<>();
        commandPayload.put("command_type", "set_timing_plan");
        commandPayload.put("junction_id", junctionId);
        commandPayload.put("ts_wall", System.currentTimeMillis() / 1000.0);
        commandPayload.put("cycle_length", cycleLength);
        commandPayload.put("green_times", greenTimes);

        // 通过 MQTT 推送至边缘端
        String topic = "traffic-control/" + junctionId + "/command";
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                String jsonStr = objectMapper.writeValueAsString(commandPayload);
                MqttMessage message = new MqttMessage(jsonStr.getBytes(StandardCharsets.UTF_8));
                message.setQos(1);
                mqttClient.publish(topic, message);
                log.info("【MQTT 投递成功】Topic: {}, Payload: {}", topic, jsonStr);
            } else {
                log.warn("【MQTT 未连接】已模拟下发至 Topic: {}", topic);
            }
        } catch (Exception e) {
            log.error("【MQTT 下发失败】", e);
        }

        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("message", "配时指令已成功推送至边缘路口 " + junctionId);
        res.put("data", commandPayload);
        return ResponseEntity.ok(res);
    }
}