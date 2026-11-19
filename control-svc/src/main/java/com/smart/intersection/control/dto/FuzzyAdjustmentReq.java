package com.smart.intersection.control.dto;

import lombok.Data;

@Data
public class FuzzyAdjustmentReq {
    private String intersectionId;
    private String currentPhase;
    private Integer currentGreenTime; // 当前已执行绿灯时长 (秒)
    private Integer queueLength;      // 当前相位排队长度 (辆)
    private Integer arrivalRate;      // 冲突相位到达率 (辆/分钟)
}