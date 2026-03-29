package com.medical.repository;

import com.medical.entity.PrivacyConfig;
import org.apache.ibatis.annotations.*;

@Mapper
public interface PrivacyRepository {
    @Select("SELECT * FROM privacy_config WHERE user_id = #{userId}")
    PrivacyConfig findByUserId(Long userId);
    
    @Update("UPDATE privacy_config SET epsilon=#{epsilon}, delta=#{delta}, sensitivity=#{sensitivity}, " +
            "noise_mechanism=#{noiseMechanism}, application_stage=#{applicationStage}, privacy_budget=#{privacyBudget} " +
            "WHERE user_id=#{userId}")
    int update(PrivacyConfig config);
}
