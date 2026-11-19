package com.smart.intersection.dispatch.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "dispatch_log")
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DispatchLogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "intersection_id")
    private String intersectionId;

    @Column(name = "command_type")
    private String commandType;

    @Column(name = "payload", columnDefinition = "TEXT")
    private String payload;

    @Column(name = "status")
    private String status;

    @Column(name = "message")
    private String message;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    /**
     * 保存前的持久化拦截：确保 commandType, status, createTime 永远不为空
     */
    @PrePersist
    public void prePersist() {
        if (this.createTime == null) {
            this.createTime = LocalDateTime.now();
        }
        if (this.commandType == null || this.commandType.trim().isEmpty()) {
            this.commandType = "SIGNAL_TIMING";
        }
        if (this.status == null || this.status.trim().isEmpty()) {
            this.status = "SUCCESS";
        }
    }
}