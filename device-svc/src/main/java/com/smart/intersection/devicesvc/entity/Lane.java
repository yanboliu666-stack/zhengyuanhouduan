package com.smart.intersection.devicesvc.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("lane")
public class Lane {
    @TableId(type = IdType.INPUT)
    private String id;             // 例如: E_L1
    private String intersectionId; // 所属路口
    private String laneCode;       // 车道编号
    private String direction;      // STRAIGHT / LEFT / RIGHT
    private String roiPolygon;     // 多边形标定坐标 (JSON)
    private Integer sortOrder;
    private LocalDateTime createdAt;
}