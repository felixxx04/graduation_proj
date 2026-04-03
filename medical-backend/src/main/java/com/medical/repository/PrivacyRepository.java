package com.medical.repository;

import com.medical.entity.PrivacyConfig;
import org.apache.ibatis.annotations.*;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface PrivacyRepository {

    @Select("SELECT * FROM privacy_config WHERE user_id = #{userId}")
    PrivacyConfig findByUserId(Long userId);

    @Update("UPDATE privacy_config SET epsilon=#{epsilon}, delta=#{delta}, sensitivity=#{sensitivity}, " +
            "noise_mechanism=#{noiseMechanism}, application_stage=#{applicationStage}, privacy_budget=#{privacyBudget} " +
            "WHERE user_id=#{userId}")
    int update(PrivacyConfig config);

    @Update("UPDATE privacy_config SET budget_used = budget_used + #{epsilon} WHERE user_id = #{userId}")
    int addBudgetUsed(@Param("userId") Long userId, @Param("epsilon") BigDecimal epsilon);

    @Select("SELECT budget_used FROM privacy_config WHERE user_id = #{userId}")
    BigDecimal getBudgetUsed(Long userId);

    // Privacy Ledger operations
    @Insert("""
        INSERT INTO privacy_ledger (user_id, event_type, epsilon_spent, delta_spent, noise_mechanism, note, created_at)
        VALUES (#{userId}, #{eventType}, #{epsilonSpent}, #{deltaSpent}, #{noiseMechanism}, #{note}, NOW())
        """)
    int insertLedgerEvent(Map<String, Object> params);

    @Select("SELECT * FROM privacy_ledger WHERE user_id = #{userId} ORDER BY created_at DESC LIMIT #{limit}")
    List<Map<String, Object>> findLedgerEventsByUserId(@Param("userId") Long userId, @Param("limit") int limit);

    @Select("SELECT COUNT(*) FROM privacy_ledger")
    int countLedgerEvents();

    @Delete("DELETE FROM privacy_ledger")
    int clearLedger();
}
