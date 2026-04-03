package com.medical.service;

import com.medical.dto.request.PatientRequest;
import com.medical.dto.response.PatientProfile;
import com.medical.entity.HealthRecord;
import com.medical.entity.Patient;
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

    public PatientProfile getPatientById(Long id) {
        return patientRepository.findProfileById(id);
    }

    @Transactional
    public PatientProfile createPatient(PatientRequest request) {
        // 1. 创建患者基础信息
        Patient patient = new Patient();
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
            return null;
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
