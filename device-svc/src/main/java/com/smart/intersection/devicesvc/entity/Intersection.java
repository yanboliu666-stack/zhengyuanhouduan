package com.smart.intersection.devicesvc.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("intersection")
public class Intersection {
    @TableId(type = IdType.INPUT)
    private String id;           // 例如: INT_001
    private String name;         // 路口名称
    private Double longitude;    // 经度
    private Double latitude;     // 纬度
    private String roadType;     // CROSS / T_JUNCTION
    private String controlMode;  // FIXED / WEBSTER / FUZZY / GREEN_WAVE
    private String status;       // ACTIVE / INACTIVE
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}