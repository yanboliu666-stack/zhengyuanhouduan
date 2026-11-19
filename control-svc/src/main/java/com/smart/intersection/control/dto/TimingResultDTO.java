package com.smart.intersection.control.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TimingResultDTO {
    private Integer cycleLength;
    private Double totalLostTime;
    private Double flowRatioSum;
    private List<Integer> greenTimes;
}