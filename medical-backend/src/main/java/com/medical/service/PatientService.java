package com.medical.service;

import com.medical.dto.request.ClinicalMetricsRequest;
import com.medical.dto.request.PatientRequest;
import com.medical.dto.response.PatientProfile;
import com.medical.entity.HealthRecord;
import com.medical.entity.Patient;
import com.medical.exception.ResourceNotFoundException;
import com.medical.repository.HealthRecordRepository;
import com.medical.repository.PatientRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class PatientService {
    private final PatientRepository patientRepository;
    private final HealthRecordRepository healthRecordRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<PatientProfile> getAllPatients() {
        return patientRepository.findAllProfiles();
    }

    public List<PatientProfile> getMyPatients(Long userId) {
        return patientRepository.findProfilesByUserId(userId);
    }
    }

    public PatientProfile getPatientById(Long id) {
        PatientProfile profile = patientRepository.findProfileById(id);
        if (profile == null) {
            throw new ResourceNotFoundException("患者不存在: id=" + id);
        }
        return profile;
    }

    @Transactional
    public PatientProfile createPatient(PatientRequest request) {
        return createPatient(request, null);
    }

    @Transactional
    public PatientProfile createPatient(PatientRequest request, Long userId) {
        // 1. 创建患者基础信息
        Patient patient = new Patient();
        patient.setUserId(userId);
        patient.setName(request.getName());
        patient.setGender(request.getGender());
        patient.setBirthDate(calculateBirthDate(request.getAge()));
        patient.setPhone(request.getPhone());
        patientRepository.insert(patient);

        // 2. 创建健康档案
        HealthRecord record = createHealthRecord(patient.getId(), request);
        healthRecordRepository.insert(record);

        return patientRepository.findProfileById(patient.getId());
    }

    @Transactional
    public PatientProfile updatePatient(Long id, PatientRequest request) {
        // 检查患者是否存在
        Patient existing = patientRepository.findById(id);
        if (existing == null) {
            throw new ResourceNotFoundException("患者不存在: id=" + id);
        }

        // 1. 更新患者基础信息
        existing.setName(request.getName());
        existing.setGender(request.getGender());
        existing.setBirthDate(calculateBirthDate(request.getAge()));
        existing.setPhone(request.getPhone());
        patientRepository.update(existing);

        // 2. 更新健康档案（标记旧记录，创建新记录）
        healthRecordRepository.markAllAsNotLatest(id);
        HealthRecord record = createHealthRecord(id, request);
        healthRecordRepository.insert(record);

        return patientRepository.findProfileById(id);
    }

    @Transactional
    public void deletePatient(Long id) {
        healthRecordRepository.deleteByPatientId(id);
        patientRepository.deleteById(id);
    }

    @Transactional
    public void updateClinicalMetrics(Long patientId, ClinicalMetricsRequest request) {
        HealthRecord latest = healthRecordRepository.findLatestByPatientId(patientId);
        if (latest == null) {
            latest = new HealthRecord();
            latest.setPatientId(patientId);
            latest.setRecordDate(LocalDate.now());
            latest.setIsLatest(true);
        }
        if (request.getRenalFunction() != null)
            latest.setRenalFunction(request.getRenalFunction());
        if (request.getHepaticFunction() != null)
            latest.setHepaticFunction(request.getHepaticFunction());
        if (request.getSmokingStatus() != null)
            latest.setSmokingStatus(request.getSmokingStatus());
        if (request.getDrinkingStatus() != null)
            latest.setDrinkingStatus(request.getDrinkingStatus());
        if (request.getBloodPressureSystolic() != null)
            latest.setBloodPressureSystolic(request.getBloodPressureSystolic());
        if (request.getBloodPressureDiastolic() != null)
            latest.setBloodPressureDiastolic(request.getBloodPressureDiastolic());
        if (request.getFastingGlucose() != null)
            latest.setFastingGlucose(request.getFastingGlucose());
        if (request.getHba1c() != null)
            latest.setHba1c(request.getHba1c());
        if (request.getCholesterolTotal() != null)
            latest.setCholesterolTotal(request.getCholesterolTotal());
        if (request.getCholesterolLdl() != null)
            latest.setCholesterolLdl(request.getCholesterolLdl());
        if (request.getHeartRate() != null)
            latest.setHeartRate(request.getHeartRate());

        if (latest.getId() == null) {
            healthRecordRepository.insert(latest);
        } else {
            healthRecordRepository.update(latest);
        }
    }

    private LocalDate calculateBirthDate(Integer age) {
        if (age == null || age <= 0) {
            return LocalDate.now().minusYears(45); // 默认45岁
        }
        return LocalDate.now().minusYears(age);
    }

    private HealthRecord createHealthRecord(Long patientId, PatientRequest request) {
        HealthRecord record = new HealthRecord();
        record.setPatientId(patientId);
        record.setRecordDate(LocalDate.now());
        record.setAge(request.getAge());
        record.setHeight(request.getHeight() != null ? BigDecimal.valueOf(request.getHeight()) : null);
        record.setWeight(request.getWeight() != null ? BigDecimal.valueOf(request.getWeight()) : null);
        record.setBloodType(request.getBloodType());
        record.setChronicDiseases(toJson(request.getChronicDiseases()));
        record.setAllergies(toJson(request.getAllergies()));
        record.setCurrentMedications(toJson(request.getCurrentMedications()));
        record.setMedicalHistory(request.getMedicalHistory());
        record.setSymptoms(request.getSymptoms());
        record.setIsLatest(true);
        record.setRenalFunction(request.getRenalFunction());
        record.setHepaticFunction(request.getHepaticFunction());
        record.setSmokingStatus(request.getSmokingStatus());
        record.setDrinkingStatus(request.getDrinkingStatus());
        record.setBloodPressureSystolic(request.getBloodPressureSystolic());
        record.setBloodPressureDiastolic(request.getBloodPressureDiastolic());
        record.setFastingGlucose(request.getFastingGlucose());
        record.setHba1c(request.getHba1c());
        record.setCholesterolTotal(request.getCholesterolTotal());
        record.setCholesterolLdl(request.getCholesterolLdl());
        record.setHeartRate(request.getHeartRate());
        return record;
    }

    private String toJson(List<String> list) {
        if (list == null || list.isEmpty()) {
            return "[]";
        }
        try {
            return objectMapper.writeValueAsString(list);
        } catch (JsonProcessingException e) {
            return "[]";
        }
    }
}
