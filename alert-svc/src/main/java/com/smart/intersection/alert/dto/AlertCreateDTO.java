package com.smart.intersection.alert.dto;

import lombok.Data;

@Data
public class AlertCreateDTO {
    private String intersectionId;
    private String alertType;  // CONGESTION, DEVICE_OFFLINE, SIGNAL_CONFLICT
    private String alertLevel; // WARNING, CRITICAL
    private String message;
}