package com.smart.intersection.dispatch.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DispatchReqDTO {

    private String intersectionId;
    private String commandType;
    private List<Integer> greenTimes;
    private Integer cycleLength;
    private Object payload;
}