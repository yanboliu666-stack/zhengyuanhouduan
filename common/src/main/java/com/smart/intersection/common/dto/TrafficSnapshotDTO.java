package com.smart.intersection.common.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class TrafficSnapshotDTO {
    private String intersectionId;
    private String laneId;
    private String direction;    // STRAIGHT / LEFT / RIGHT
    private Integer count;
    private Integer occupancy;
    private Double queueLen;
    private Integer queueVehicles;
    private Double avgSpeed;
    private Double avgPassTime;
    private Integer phaseId;
    private LocalDateTime timestamp;
}