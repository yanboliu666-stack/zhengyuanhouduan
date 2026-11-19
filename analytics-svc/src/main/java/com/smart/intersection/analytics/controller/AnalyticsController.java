package com.smart.intersection.analytics.controller;

import com.smart.intersection.analytics.dto.CongestionIndexDTO;
import com.smart.intersection.analytics.service.TrafficAnalyticsService;
import com.smart.intersection.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/analytics")
public class AnalyticsController {

    @Autowired
    private TrafficAnalyticsService analyticsService;

    // 1. 实时拥堵指数
    @GetMapping("/congestion/{intersectionId}")
    public Result<?> getCongestion(@PathVariable("intersectionId") String intersectionId) {
        try {
            CongestionIndexDTO dto = analyticsService.calculateCongestion(intersectionId);
            return Result.success(dto);
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("拥堵指数计算异常: " + e.getMessage());
        }
    }

    // 2. 流量趋势
    @GetMapping("/trend/{intersectionId}")
    public Result<?> getTrend(@PathVariable("intersectionId") String intersectionId) {
        try {
            List<Map<String, Object>> trend = analyticsService.getHistoryTrend(intersectionId);
            return Result.success(trend);
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("流量趋势查询异常: " + e.getMessage());
        }
    }
}