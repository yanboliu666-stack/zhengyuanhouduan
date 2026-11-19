package com.smart.intersection.alert.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_alert_record")
public class AlertRecordEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "intersection_id", nullable = false)
    private String intersectionId;

    @Column(name = "alert_type", nullable = false)
    private String alertType; // CONGESTION(严重拥堵), DEVICE_OFFLINE(设备掉线), SIGNAL_CONFLICT(绿冲突)

    @Column(name = "alert_level", nullable = false)
    private String alertLevel; // INFO, WARNING, CRITICAL

    @Column(name = "message", nullable = false)
    private String message;

    @Column(name = "status")
    private String status = "UNRESOLVED"; // UNRESOLVED(未消除), RESOLVED(已消除)

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}