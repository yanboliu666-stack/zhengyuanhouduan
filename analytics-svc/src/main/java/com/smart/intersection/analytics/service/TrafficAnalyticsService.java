package com.smart.intersection.analytics.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smart.intersection.analytics.dto.CongestionIndexDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class TrafficAnalyticsService {

    @Autowired(required = false)
    private StringRedisTemplate stringRedisTemplate;

    @Autowired(required = false)
    private JdbcTemplate jdbcTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public CongestionIndexDTO calculateCongestion(String intersectionId) {
        CongestionIndexDTO dto = new CongestionIndexDTO();
        dto.setIntersectionId(intersectionId);

        double totalQueue = 0;
        int laneCount = 0;

        if (stringRedisTemplate != null) {
            try {
                Set<String> keys = stringRedisTemplate.keys("realtime:" + intersectionId + ":*");
                if (keys != null) {
                    for (String key : keys) {
                        String val = stringRedisTemplate.opsForValue().get(key);
                        if (val != null) {
                            Map<String, Object> data = objectMapper.readValue(val, Map.class);
                            totalQueue += ((Number) data.getOrDefault("queueLength", 0)).doubleValue();
                            laneCount++;
                        }
                    }
                }
            } catch (Exception ignored) {}
        }

        double avgQueue = laneCount > 0 ? totalQueue / laneCount : 0;
        double index = Math.min(100.0, (avgQueue / 15.0) * 100.0);

        dto.setTotalIndex(Math.round(index * 100.0) / 100.0);
        if (index < 30) dto.setStatus("流畅");
        else if (index < 70) dto.setStatus("缓行");
        else dto.setStatus("拥堵");

        return dto;
    }

    public List<Map<String, Object>> getHistoryTrend(String intersectionId) {
        if (jdbcTemplate == null) {
            return new ArrayList<>();
        }
        String sql = "SELECT COUNT(*) as cnt FROM lane_traffic WHERE intersection_id = '" + intersectionId + "'";
        try {
            return jdbcTemplate.queryForList(sql);
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }
}