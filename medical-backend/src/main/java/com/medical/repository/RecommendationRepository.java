package com.medical.repository;

import com.medical.entity.Recommendation;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface RecommendationRepository {

    @Select("SELECT * FROM recommendation ORDER BY created_at DESC")
    List<Recommendation> findAll();

    @Select("SELECT * FROM recommendation WHERE patient_id = #{patientId} ORDER BY created_at DESC")
    List<Recommendation> findByPatientId(Long patientId);

    @Select("SELECT COUNT(*) FROM recommendation")
    int countAll();

    @Insert("""
        INSERT INTO recommendation
        (patient_id, user_id, input_data, result_data, dp_enabled, epsilon_used, recommendation_type)
        VALUES (#{patientId}, #{userId}, #{inputData}, #{resultData}, #{dpEnabled}, #{epsilonUsed}, #{recommendationType})
        """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Recommendation recommendation);

    @Select("SELECT COUNT(*) FROM recommendation WHERE DATE(created_at) = CURDATE()")
    int countToday();
}
