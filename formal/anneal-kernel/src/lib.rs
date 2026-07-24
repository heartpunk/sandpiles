//! Small proof-kernel functions shared by the sandpile formalization.
//!
//! This crate deliberately starts with the two arithmetic identities at the
//! end of a once-each toppling schedule.  Keeping the first Anneal target tiny
//! makes the trust boundary visible: Rust executes these functions, Charon and
//! Aeneas translate them, and Lean must prove both exactness and stability.

/// Checks and computes the final height of a non-trigger cell that started at
/// height three, toppled once, and received one grain from each of its
/// `degree` active neighbors.
///
/// `None` rejects degrees for which that once-each schedule is not a stable
/// unit-toppling schedule.
///
/// ```lean, anneal, spec
/// ensures (h_result):
///   match ret with
///   | .none => degree.val = 0 ∨ degree.val > 4
///   | .some height =>
///     degree.val >= 1 ∧
///     degree.val <= 4 ∧
///     height.val + 1 = degree.val ∧
///     height.val <= 3
/// proof (h_progress):
///   unfold nontrigger_final_height
///   split
///   · simp_all
///   · split
///     · simp_all
///     ·
///       have h_le : (1#u8).val <= degree.val := by scalar_tac
///       have h_sub := U8.sub_spec (x := degree) (y := 1#u8) h_le
///       rcases Aeneas.Std.WP.spec_imp_exists h_sub with
///         ⟨height, h_sub_eq, _⟩
///       rw [h_sub_eq, Aeneas.Std.bind_tc_ok]
///       exact ⟨some height, rfl⟩
/// proof (h_result):
///   unfold nontrigger_final_height at h_returns
///   split at h_returns
///   · cases ret <;> simp_all
///   · split at h_returns
///     · cases ret <;> simp_all
///     ·
///       have h_le : (1#u8).val <= degree.val := by scalar_tac
///       have h_sub := U8.sub_spec (x := degree) (y := 1#u8) h_le
///       rcases Aeneas.Std.WP.spec_imp_exists h_sub with
///         ⟨height, h_sub_eq, h_height⟩
///       rw [h_sub_eq, Aeneas.Std.bind_tc_ok] at h_returns
///       cases ret <;> simp_all
/// ```
pub fn nontrigger_final_height(degree: u8) -> Option<u8> {
    if degree == 0 || degree > 4 {
        None
    } else {
        Some(degree - 1)
    }
}

/// Checks and computes the final height of the trigger cell. It starts at
/// height four after the trigger grain, topples once, and receives one grain
/// from each active neighbor.
///
/// `None` rejects degrees for which that once-each schedule does not finish
/// stable.
///
/// ```lean, anneal, spec
/// ensures (h_result):
///   match ret with
///   | .none => degree.val > 3
///   | .some height => height = degree ∧ height.val <= 3
/// proof (h_progress):
///   unfold trigger_final_height
///   split <;> simp_all
/// proof (h_result):
///   unfold trigger_final_height at h_returns
///   split at h_returns <;> cases ret <;> simp_all
/// ```
pub fn trigger_final_height(degree: u8) -> Option<u8> {
    if degree <= 3 { Some(degree) } else { None }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn local_final_heights_are_stable() {
        for degree in 1..=4 {
            let height = nontrigger_final_height(degree).unwrap();
            assert_eq!(height, degree - 1);
            assert!(height <= 3);
        }
        assert_eq!(nontrigger_final_height(0), None);
        assert_eq!(nontrigger_final_height(5), None);
        for degree in 0..=3 {
            let height = trigger_final_height(degree).unwrap();
            assert_eq!(height, degree);
            assert!(height <= 3);
        }
        assert_eq!(trigger_final_height(4), None);
    }
}
