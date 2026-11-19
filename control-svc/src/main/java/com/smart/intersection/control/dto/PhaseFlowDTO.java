package com.smart.intersection.control.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PhaseFlowDTO {
    private String phaseName;    // 相位名称，如 "东西直行"
    private Integer flowRate;    // 实际交通流量 q (veh/h)
    private Integer satFlowRate; // 饱和流量 s (veh/h)，默认 1800
}