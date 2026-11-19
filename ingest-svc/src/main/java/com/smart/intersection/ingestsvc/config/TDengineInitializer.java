package com.smart.intersection.ingestsvc.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Component
public class TDengineInitializer implements CommandLineRunner {

    @Value("${tdengine.rest-url:http://localhost:6041/rest/sql}")
    private String tdengineUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    @Override
    public void run(String... args) {
        try {
            log.info("初始化 TDengine 数据库与超级表...");
            executeSql("CREATE DATABASE IF NOT EXISTS smart_traffic;");
            executeSql("CREATE STABLE IF NOT EXISTS smart_traffic.lane_traffic (ts TIMESTAMP, vehicle_count INT, avg_speed DOUBLE) TAGS (intersection_id VARCHAR(32), lane_id VARCHAR(32));");
            log.info("TDengine 数据库与超级表初始化成功！");
        } catch (Exception e) {
            log.warn("TDengine 初始化通知: {}", e.getMessage());
        }
    }

    private void executeSql(String sql) {
        try {
            restTemplate.postForObject(tdengineUrl, sql, String.class);
        } catch (Exception e) {
            log.warn("执行 TDengine REST SQL 异常: {}", e.getMessage());
        }
    }
}