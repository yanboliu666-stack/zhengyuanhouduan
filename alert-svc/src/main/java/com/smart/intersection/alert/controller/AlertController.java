package com.smart.intersection.alert.controller;

import com.smart.intersection.alert.dto.AlertCreateDTO;
import com.smart.intersection.alert.entity.AlertRecordEntity;
import com.smart.intersection.alert.service.AlertService;
import com.smart.intersection.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/alerts")
public class AlertController {

    @Autowired
    private AlertService alertService;

    // 1. 上报/触发新告警
    @PostMapping
    public Result<AlertRecordEntity> createAlert(@RequestBody AlertCreateDTO dto) {
        AlertRecordEntity entity = alertService.createAlert(dto);
        return Result.success(entity);
    }

    // 2. 查询指定交叉口的所有告警记录
    @GetMapping("/{intersectionId}")
    public Result<List<AlertRecordEntity>> getAlerts(@PathVariable("intersectionId") String intersectionId) {
        List<AlertRecordEntity> alerts = alertService.getAlertsByIntersection(intersectionId);
        return Result.success(alerts);
    }

    // 3. 消除/标记恢复指定告警
    @PutMapping("/{alertId}/resolve")
    public Result<AlertRecordEntity> resolveAlert(@PathVariable("alertId") Long alertId) {
        AlertRecordEntity entity = alertService.resolveAlert(alertId);
        return Result.success(entity);
    }
}