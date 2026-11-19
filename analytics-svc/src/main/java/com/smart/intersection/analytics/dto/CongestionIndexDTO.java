package com.smart.intersection.analytics.dto;

import lombok.Data;
import java.util.Map;

@Data
public class CongestionIndexDTO {
    private String intersectionId;
    private Double totalIndex; // 0-100，越高越拥堵
    private String status;     // 流畅, 缓行, 拥堵
    private Map<String, Double> laneIndices; // 各车道详情
}