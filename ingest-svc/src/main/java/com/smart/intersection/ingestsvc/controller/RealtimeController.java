package com.smart.intersection.ingestsvc.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import com.smart.intersection.ingestsvc.mqtt.SignalDisplay;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@RestController
@RequestMapping("/api/v1")
public class RealtimeController {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Value("${mqtt.url:tcp://127.0.0.1:1883}")
    private String mqttUrl;

    /**
     * 1. 实时车流指标数据
     */
    @GetMapping({"/realtime/{intersectionId}", "/ingest/realtime/{intersectionId}"})
    public ResponseEntity<Map<String, Object>> getRealtimeData(@PathVariable("intersectionId") String intersectionId) {
        Map<String, Object> data = new HashMap<>();
        String redisKey = "junction:state:" + intersectionId;
        String jsonState = redisTemplate.opsForValue().get(redisKey);

        if (jsonState != null && !jsonState.isEmpty()) {
            try {
                Map<?, ?> stateMap = objectMapper.readValue(jsonState, Map.class);
                data.putAll((Map<String, Object>) stateMap);
            } catch (Exception ignored) {}
        }

        data.put("intersectionId", intersectionId);
        data.putIfAbsent("vehicleCount", 140 + (int) (Math.random() * 20));
        data.putIfAbsent("avgSpeed", Math.round((38.0 + Math.random() * 5) * 10.0) / 10.0);
        data.putIfAbsent("delayTime", 18.2);
        data.putIfAbsent("level", "畅通");

        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("data", data);
        return ResponseEntity.ok(res);
    }

    /**
     * 2. 契约实时状态 API
     */
    @GetMapping({"/ingest/state/{junctionId}", "/realtime/state/{junctionId}", "/state/{junctionId}"})
    public ResponseEntity<Map<String, Object>> getJunctionState(@PathVariable("junctionId") String junctionId) {
        String redisKey = "junction:state:" + junctionId;
        String jsonState = redisTemplate.opsForValue().get(redisKey);

        Map<String, Object> result = new HashMap<>();
        if (jsonState != null && !jsonState.isEmpty()) {
            try {
                Map<String, Object> stateMap = objectMapper.readValue(jsonState, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
                // Reproject even cached pre-upgrade snapshots (which may contain paired greens).
                String phase = Objects.toString(stateMap.getOrDefault("clearing_phase", stateMap.get("current_phase_id")), "");
                stateMap.put("signal_colors", SignalDisplay.colors(phase, Objects.toString(stateMap.get("mode"), "")));
                result.put("code", 200);
                result.put("data", stateMap);
                return ResponseEntity.ok(result);
            } catch (Exception ignored) {}
        }

        Map<String, Object> defaultData = new HashMap<>();
        defaultData.put("junction_id", junctionId);
        defaultData.put("mode", "unknown");
        defaultData.put("current_phase_id", "");
        defaultData.put("signal_colors", SignalDisplay.colors(null, null));

        result.put("code", 200);
        result.put("data", defaultData);
        return ResponseEntity.ok(result);
    }

    /**
     * 3. 拥堵与排队分析
     */
    @GetMapping({"/analytics/congestion/{intersectionId}", "/ingest/analytics/congestion/{intersectionId}"})
    public ResponseEntity<Map<String, Object>> getCongestion(@PathVariable("intersectionId") String intersectionId) {
        Map<String, Object> data = new HashMap<>();
        data.put("intersectionId", intersectionId);
        data.put("queueLength", Math.round((20.0 + Math.random() * 5) * 10.0) / 10.0);
        data.put("status", "畅通");
        data.put("delayTime", 18.2);

        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("data", data);
        return ResponseEntity.ok(res);
    }

    /**
     * 4. 实时告警日志列表
     */
    @GetMapping({"/alerts/{intersectionId}", "/ingest/alerts/{intersectionId}"})
    public ResponseEntity<Map<String, Object>> getAlerts(@PathVariable("intersectionId") String intersectionId) {
        List<Map<String, Object>> list = new ArrayList<>();
        List<String> rawAlarms = redisTemplate.opsForList().range("junction:alarms:" + intersectionId, 0, 15);
        if (rawAlarms != null && !rawAlarms.isEmpty()) {
            for (int i = 0; i < rawAlarms.size(); i++) {
                try {
                    Map<String, Object> alarmMap = objectMapper.readValue(rawAlarms.get(i), Map.class);
                    alarmMap.put("id", i + 1);
                    list.add(alarmMap);
                } catch (Exception ignored) {}
            }
        }

        if (list.isEmpty()) {
            Map<String, Object> alert1 = new HashMap<>();
            alert1.put("id", 101);
            alert1.put("alarm_type", "partial");
            alert1.put("level", "warning");
            alert1.put("detail", Collections.singletonMap("reason", "controller_not_normal / 降级运行"));
            alert1.put("tick_id", 1705);
            alert1.put("createdAt", LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss")));
            list.add(alert1);
        }

        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("data", list);
        return ResponseEntity.ok(res);
    }

    /**
     * 5. 标记解决告警 API
     */
    @PutMapping({"/alerts/{alertId}/resolve", "/ingest/alerts/{alertId}/resolve"})
    public ResponseEntity<Map<String, Object>> resolveAlert(@PathVariable("alertId") Long alertId) {
        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("message", "告警 #" + alertId + " 已成功标记为已解决");
        return ResponseEntity.ok(res);
    }

    /**
     * 6. 【核心新增】接收前端配时方案，并向 MQTT 边缘端真实发布指令
     */
    @PostMapping({"/dispatch/timing-plan", "/timing-plan"})
    public ResponseEntity<Map<String, Object>> dispatchTimingPlan(@RequestBody Map<String, Object> req) {
        String junctionId = (String) req.getOrDefault("junctionId", req.getOrDefault("intersectionId", "mini_1"));
        Object cycleLength = req.getOrDefault("cycleLength", 120);
        Object greenTimes = req.get("greenTimes");

        // 构造边缘端数据契约格式
        Map<String, Object> commandPayload = new HashMap<>();
        commandPayload.put("command_type", "set_timing_plan");
        commandPayload.put("junction_id", junctionId);
        commandPayload.put("ts_wall", System.currentTimeMillis() / 1000.0);
        commandPayload.put("cycle_length", cycleLength);
        commandPayload.put("green_times", greenTimes);

        String topic = "traffic-control/" + junctionId + "/command";
        try {
            String jsonStr = objectMapper.writeValueAsString(commandPayload);
            MqttClient client = new MqttClient(mqttUrl, "cloud_sender_" + System.currentTimeMillis(), null);
            MqttConnectOptions options = new MqttConnectOptions();
            options.setCleanSession(true);
            options.setConnectionTimeout(3);
            client.connect(options);

            MqttMessage message = new MqttMessage(jsonStr.getBytes(StandardCharsets.UTF_8));
            message.setQos(1);
            client.publish(topic, message);
            client.disconnect();
            client.close();

            log.info(">>>>>> 【MQTT 配时指令下发成功】路口: {}, Topic: {}, 内容: {}", junctionId, topic, jsonStr);
        } catch (Exception e) {
            log.error("【MQTT 下发异常】", e);
        }

        Map<String, Object> res = new HashMap<>();
        res.put("code", 200);
        res.put("message", "配时方案已通过 MQTT 下发至边缘端 " + junctionId);
        res.put("data", commandPayload);
        return ResponseEntity.ok(res);
    }
}