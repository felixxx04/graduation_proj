package com.medical.dto.request;

import jakarta.validation.constraints.*;
import lombok.Data;
import java.util.List;

@Data
public class PatientRequest {
    @NotBlank(message = "姓名不能为空")
    @Size(max = 50, message = "姓名长度不能超过50")
    private String name;

    @NotBlank(message = "性别不能为空")
    @Pattern(regexp = "MALE|FEMALE|UNKNOWN", message = "性别必须为 MALE/FEMALE/UNKNOWN")
    private String gender;

    @NotNull(message = "年龄不能为空")
    @Min(value = 0, message = "年龄不能为负数")
    @Max(value = 150, message = "年龄不能超过150")
    private Integer age;

    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    @DecimalMin(value = "0.1", message = "身高必须大于0")
    @DecimalMax(value = "300", message = "身高不能超过300cm")
    private Double height;

    @DecimalMin(value = "0.1", message = "体重必须大于0")
    @DecimalMax(value = "500", message = "体重不能超过500kg")
    private Double weight;

    @Pattern(regexp = "A|B|AB|O", message = "血型必须为 A/B/AB/O")
    private String bloodType;

    private List<String> allergies;
    private List<String> chronicDiseases;
    private List<String> currentMedications;

    @Size(max = 2000, message = "病史描述不能超过2000字")
    private String medicalHistory;

    @Size(max = 2000, message = "症状描述不能超过2000字")
    private String symptoms;
}
