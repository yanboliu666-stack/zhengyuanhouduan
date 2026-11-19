package com.smart.intersection.control.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_signal_plan")
public class SignalPlanEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "intersection_id", nullable = false)
    private String intersectionId;

    @Column(name = "control_mode", nullable = false)
    private String controlMode; // WEBSTER, FUZZY

    @Column(name = "cycle_length")
    private Integer cycleLength; // 最佳周期时长(秒)

    @Column(name = "phase_split_json", columnDefinition = "TEXT")
    private String phaseSplitJson; // 各相位绿灯时间分配 JSON

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}