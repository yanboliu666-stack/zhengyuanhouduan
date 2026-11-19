package com.smart.intersection.authsvc.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("sys_user")
public class SysUser {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String username;
    private String password;
    private String role;
    private String status; // 【关键修改】从 Integer 改为 String，匹配数据库里的 "ACTIVE"
    private LocalDateTime created_at; // 匹配你截图里的字段名 created_at
}