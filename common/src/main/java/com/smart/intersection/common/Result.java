package com.smart.intersection.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> {
    private Integer code;
    private String message;
    private T data;
    private Long timestamp;

    // --- 兼容 ingest-svc 的方法名 ---
    public static <T> Result<T> success() {
        return new Result<>(200, "SUCCESS", null, System.currentTimeMillis());
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(200, "SUCCESS", data, System.currentTimeMillis());
    }

    public static <T> Result<T> error(String message) {
        return new Result<>(500, message, null, System.currentTimeMillis());
    }

    // --- 兼容 auth-svc 的方法名 (别名) ---
    public static <T> Result<T> ok(T data) {
        return new Result<>(200, "SUCCESS", data, System.currentTimeMillis());
    }

    public static <T> Result<T> ok() {
        return new Result<>(200, "SUCCESS", null, System.currentTimeMillis());
    }

    public static <T> Result<T> fail(Integer code, String message) {
        return new Result<>(code, message, null, System.currentTimeMillis());
    }
}