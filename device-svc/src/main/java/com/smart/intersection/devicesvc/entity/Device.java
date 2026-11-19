package com.smart.intersection.devicesvc.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("device")
public class Device {
    @TableId(type = IdType.INPUT)
    private String id;             // 设备ID
    private String intersectionId; // 所属路口
    private String deviceType;     // CAMERA / EDGE_BOX / SIGNAL_CONTROLLER
    private String ipAddress;
    private String status;         // ONLINE / OFFLINE
    private LocalDateTime lastHeartbeat;
    private String firmwareVer;
    private LocalDateTime createdAt;
}