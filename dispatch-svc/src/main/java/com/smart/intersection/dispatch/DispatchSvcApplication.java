package com.smart.intersection.dispatch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class DispatchSvcApplication {
    public static void main(String[] args) {
        SpringApplication.run(DispatchSvcApplication.class, args);
    }
}