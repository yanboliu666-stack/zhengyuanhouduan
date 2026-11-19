package com.smart.intersection.ingestsvc.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration
public class RedisConfig {

    @Bean
    @Primary
    public LettuceConnectionFactory redisConnectionFactory() {
        // 使用 localhost 替代 127.0.0.1
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName("localhost");
        config.setPort(6379);
        config.setPassword("redis123");

        LettuceConnectionFactory factory = new LettuceConnectionFactory(config);
        // 强制立即初始化，防止懒加载导致的 unresolved 错误
        factory.afterPropertiesSet();
        return factory;
    }

    @Bean
    @Primary
    public StringRedisTemplate stringRedisTemplate(LettuceConnectionFactory factory) {
        // 使用 StringRedisTemplate 性能更高且不容易序列化报错
        return new StringRedisTemplate(factory);
    }
}