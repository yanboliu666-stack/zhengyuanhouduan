package com.smart.intersection.control.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.ArrayList;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class TimingCalculationReq {
    private String intersectionId;
    private List<Double> flows;
    private Double totalLostTime;
    private Double saturationFlow;

    public List<Double> extractFlowList() {
        if (flows == null || flows.isEmpty()) {
            return List.of(600.0, 400.0, 500.0, 300.0); // 默认兜底数据
        }
        return flows;
    }
}