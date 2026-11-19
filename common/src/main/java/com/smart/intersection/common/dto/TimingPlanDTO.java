package com.smart.intersection.common.dto;

import lombok.Data;
import java.util.List;

@Data
public class TimingPlanDTO {
    private String intersectionId;
    private Integer cycleLength;
    private String strategy;     // WEBSTER / FUZZY / GREEN_WAVE / HYBRID
    private List<PhaseTimingDTO> phases;

    @Data
    public static class PhaseTimingDTO {
        private Integer phaseId;
        private Integer green;
        private Integer yellow;
        private Integer allRed;
    }
}