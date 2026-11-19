package com.smart.intersection.authsvc;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient; // 导入包

@SpringBootApplication
@EnableDiscoveryClient // <-- 加上这一行，显式开启 Nacos 注册
@MapperScan("com.smart.intersection.authsvc.mapper")
public class AuthSvcApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuthSvcApplication.class, args);
    }
}