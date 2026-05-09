package com.medical.repository;

import com.medical.entity.ReviewLog;
import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

@Mapper
public interface ReviewLogRepository {

    @Insert("""
        INSERT INTO review_log (recommendation_id, patient_id, disease_cn,
          disease_standardized, routing_path, system_drugs, doctor_decision,
          doctor_selected_drug, doctor_reason, doctor_id)
        VALUES (#{recommendationId}, #{patientId}, #{diseaseCn},
          #{diseaseStandardized}, #{routingPath}, #{systemDrugs}, #{doctorDecision},
          #{doctorSelectedDrug}, #{doctorReason}, #{doctorId})
        """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(ReviewLog log);

    @Select("SELECT * FROM review_log WHERE id = #{id}")
    ReviewLog findById(@Param("id") Long id);

    @Select("SELECT * FROM review_log WHERE recommendation_id = #{recommendationId}")
    List<ReviewLog> findByRecommendationId(@Param("recommendationId") String recommendationId);

    @Select("SELECT * FROM review_log WHERE patient_id = #{patientId} ORDER BY created_at DESC")
    List<ReviewLog> findByPatientId(@Param("patientId") Long patientId);

    List<Map<String, Object>> getRejectionStats(
        @Param("startDate") String startDate,
        @Param("endDate") String endDate);

    List<Map<String, Object>> getModificationStats(
        @Param("startDate") String startDate,
        @Param("endDate") String endDate);

    @Select("SELECT COUNT(*) FROM review_log WHERE disease_cn = #{diseaseCn} AND doctor_decision = #{decision}")
    int countByDiseaseAndDecision(
        @Param("diseaseCn") String diseaseCn,
        @Param("decision") String decision);
}
