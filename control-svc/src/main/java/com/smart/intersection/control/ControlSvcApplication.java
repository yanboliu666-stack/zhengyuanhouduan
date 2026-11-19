package com.smart.intersection.control;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class ControlSvcApplication {
    public static void main(String[] args) {
        SpringApplication.run(ControlSvcApplication.class, args);
    }
}