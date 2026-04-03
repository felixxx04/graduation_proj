package com.medical.repository;

import com.medical.entity.HealthRecord;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface HealthRecordRepository {

    @Select("SELECT * FROM patient_health_record WHERE patient_id = #{patientId} AND is_latest = TRUE LIMIT 1")
    HealthRecord findLatestByPatientId(Long patientId);

    @Select("SELECT * FROM patient_health_record WHERE patient_id = #{patientId} ORDER BY created_at DESC")
    List<HealthRecord> findByPatientId(Long patientId);

    @Insert("""
        INSERT INTO patient_health_record
        (patient_id, record_date, age, height, weight, blood_type,
         chronic_diseases, allergies, current_medications, medical_history, symptoms, is_latest)
        VALUES (#{patientId}, #{recordDate}, #{age}, #{height}, #{weight}, #{bloodType},
                #{chronicDiseases}, #{allergies}, #{currentMedications}, #{medicalHistory}, #{symptoms}, #{isLatest})
        """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(HealthRecord record);

    @Update("UPDATE patient_health_record SET is_latest = FALSE WHERE patient_id = #{patientId}")
    int markAllAsNotLatest(Long patientId);

    @Delete("DELETE FROM patient_health_record WHERE patient_id = #{patientId}")
    int deleteByPatientId(Long patientId);
}
