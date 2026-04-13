package com.medical.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 模型服务配置类
 * 从 application.yml 或环境变量读取模型服务 URL
 */
@Configuration
@ConfigurationProperties(prefix = "model-service")
@Getter
@Setter
public class ModelServiceConfig {
    /**
     * 模型服务基础 URL
     */
    private String url = "http://localhost:8001";
    
    /**
     * 初始化超时时间（毫秒）
     */
    private int initDelayMs = 2000;
    
    /**
     * 连接超时时间（毫秒）
     */
    private int connectTimeoutMs = 5000;
    
    /**
     * 读取超时时间（毫秒）
     */
    private int readTimeoutMs = 30000;
}
