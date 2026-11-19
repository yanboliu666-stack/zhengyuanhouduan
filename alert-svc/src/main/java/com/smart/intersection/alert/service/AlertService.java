package com.smart.intersection.alert.service;

import com.smart.intersection.alert.dto.AlertCreateDTO;
import com.smart.intersection.alert.entity.AlertRecordEntity;
import com.smart.intersection.alert.repository.AlertRecordRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AlertService {

    @Autowired
    private AlertRecordRepository alertRecordRepository;

    // 1. 手动/自动触发生成告警
    public AlertRecordEntity createAlert(AlertCreateDTO dto) {
        AlertRecordEntity entity = new AlertRecordEntity();
        entity.setIntersectionId(dto.getIntersectionId());
        entity.setAlertType(dto.getAlertType());
        entity.setAlertLevel(dto.getAlertLevel());
        entity.setMessage(dto.getMessage());
        entity.setStatus("UNRESOLVED");
        return alertRecordRepository.save(entity);
    }

    // 2. 根据路口查询历史告警记录
    public List<AlertRecordEntity> getAlertsByIntersection(String intersectionId) {
        return alertRecordRepository.findByIntersectionIdOrderByCreatedAtDesc(intersectionId);
    }

    // 3. 消除告警
    public AlertRecordEntity resolveAlert(Long alertId) {
        AlertRecordEntity entity = alertRecordRepository.findById(alertId)
                .orElseThrow(() -> new RuntimeException("未找到 ID 为 " + alertId + " 的告警记录"));
        entity.setStatus("RESOLVED");
        return alertRecordRepository.save(entity);
    }
}