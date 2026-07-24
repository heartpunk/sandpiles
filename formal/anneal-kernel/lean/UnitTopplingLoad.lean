import Mathlib.Data.Finset.Card

/-!
# An exact unit-toppling load characterization

This file isolates the combinatorial core of the unit-toppling polyomino
theorem.  The active set is finite, but the ambient type need not be, so the
result can be instantiated directly on the infinite square lattice.  A
`RootedOrder` is an explicit connectedness witness:

* every active vertex occurs exactly once;
* the first vertex is the trigger; and
* every later vertex is adjacent to an earlier vertex.

The theorem proves that this order is a literal operational toppling
schedule.  It also proves an exact characterization: the once-each endpoint
is stable if and only if the trigger has at most three active neighbors and
every exterior vertex has at most three active neighbors.

For the square lattice, the additional degree assumptions follow from:

* ambient degree at most four;
* trigger internal degree at most three; and
* no exterior vertex having four active neighbors.

The file intentionally uses integer-valued heights.  Legality and final
nonnegativity show that the displayed execution never relies on truncated
subtraction.

Validated with Lean 4.30.0-rc2 and the Mathlib snapshot bundled with
`cargo-anneal 0.1.0-alpha.24`.  The file contains no `sorry`, `admit`, or
added axiom.
-/

namespace Sandpile.UnitTopplingLoad

variable {α : Type*} [DecidableEq α]
variable (adj : α → α → Prop) [DecidableRel adj]

/-- Number of vertices of `P` adjacent to `x`. -/
def neighborCount (P : Finset α) (x : α) : ℕ :=
  (P.filter fun y => adj x y).card

/--
Height-three active set, zero exterior, and one extra grain at the trigger.
-/
def initialHeight (S : Finset α) (t x : α) : ℤ :=
  (if x ∈ S then 3 else 0) + (if x = t then 1 else 0)

/--
Closed-form state after every vertex of `P` has toppled once.

The term `-4` records the toppling of `x` itself when `x ∈ P`; the neighbor
count records one incoming grain from each toppled neighbor.
-/
def stateAfter (S P : Finset α) (t x : α) : ℤ :=
  initialHeight S t x
    - (if x ∈ P then 4 else 0)
    + (neighborCount adj P x : ℤ)

/--
One threshold-four toppling at `x`.

`adj y x` means that a toppling at `x` sends one grain to `y`.  Symmetry in
the main theorem identifies this incoming-neighbor convention with ordinary
undirected adjacency.
-/
def topple (h : α → ℤ) (x : α) : α → ℤ :=
  fun y =>
    h y
      - (if y = x then 4 else 0)
      + (if adj y x then 1 else 0)

/-- State after every active vertex has toppled once. -/
def finalHeight (S : Finset α) (t x : α) : ℤ :=
  stateAfter adj S S t x

/-- Threshold-four stability, including nonnegative heights. -/
def Stable (h : α → ℤ) : Prop :=
  ∀ x, 0 ≤ h x ∧ h x < 4

/--
An explicit rooted enumeration of a finite connected active set.

The `rooted` field says that, in every decomposition at a scheduled vertex,
that vertex has not occurred in the prefix and is either the trigger in the
empty prefix or has an adjacent predecessor in the prefix.
-/
structure RootedOrder (S : Finset α) (t : α) (order : List α) : Prop where
  nodup : order.Nodup
  covers : order.toFinset = S
  trigger_mem : t ∈ S
  rooted :
    ∀ (pre : List α) (x : α) (suffix : List α),
      order = pre ++ x :: suffix →
      x ∉ pre ∧
        ((x = t ∧ pre = []) ∨
          ∃ y, y ∈ pre ∧ adj x y)

/--
Constructive rooted connectedness: existence of a once-each enumeration in
which every noninitial vertex has an earlier adjacent predecessor.

For a finite undirected graph this is equivalent to ordinary connectedness
of the induced active subgraph with root `t`.  This file uses the explicit
enumeration because it is also the desired toppling schedule.
-/
def RootConnected (S : Finset α) (t : α) : Prop :=
  ∃ order : List α, RootedOrder adj S t order

/-- Every step of `order` is legal in the closed-form prefix state. -/
def LegalSchedule (S : Finset α) (t : α) (order : List α) : Prop :=
  ∀ (pre : List α) (x : α) (suffix : List α),
    order = pre ++ x :: suffix →
    4 ≤ stateAfter adj S pre.toFinset t x

/--
The closed-form prefix states form a literal operational execution.

The first state is the initial configuration. At every decomposition of the
schedule, extending the prefix by its next vertex is exactly one application
of `topple`.
-/
def OperationalSchedule (S : Finset α) (t : α) (order : List α) : Prop :=
  stateAfter adj S ∅ t = initialHeight S t ∧
    ∀ (pre : List α) (x : α) (suffix : List α),
      order = pre ++ x :: suffix →
      stateAfter adj S (pre ++ [x]).toFinset t =
        topple adj (stateAfter adj S pre.toFinset t) x

omit [DecidableEq α] in
lemma neighborCount_pos_of_mem
    {P : Finset α} {x y : α}
    (hy : y ∈ P) (hxy : adj x y) :
    0 < neighborCount adj P x := by
  unfold neighborCount
  exact Finset.card_pos.mpr ⟨y, Finset.mem_filter.mpr ⟨hy, hxy⟩⟩

omit [DecidableEq α] in
/-- Restricting the possible senders cannot increase the neighbor count. -/
lemma neighborCount_le_univ [Fintype α] (P : Finset α) (x : α) :
    neighborCount adj P x ≤ neighborCount adj Finset.univ x := by
  unfold neighborCount
  apply Finset.card_le_card
  intro y hy
  rw [Finset.mem_filter] at hy ⊢
  exact ⟨Finset.mem_univ y, hy.2⟩

omit [DecidableEq α] in
/--
Local list decomposition helper, included to avoid depending on the name of
the corresponding convenience lemma in a particular mathlib release.
-/
lemma exists_eq_append_cons_of_mem
    {x : α} {l : List α} (hx : x ∈ l) :
    ∃ pre suffix : List α, l = pre ++ x :: suffix := by
  induction l with
  | nil =>
      simp at hx
  | cons a l ih =>
      simp only [List.mem_cons] at hx
      rcases hx with h | hx
      · subst a
        exact ⟨[], l, rfl⟩
      · obtain ⟨pre, suffix, hsplit⟩ := ih hx
        exact ⟨a :: pre, suffix, by simp [hsplit]⟩

/-- Adding one previously uncounted toppling updates every neighbor count. -/
lemma neighborCount_insert
    {P : Finset α} {x y : α} (hx : x ∉ P) :
    neighborCount adj (insert x P) y =
      neighborCount adj P y + if adj y x then 1 else 0 := by
  unfold neighborCount
  rw [Finset.filter_insert]
  by_cases hyx : adj y x
  · simp [hyx, hx]
  · simp [hyx]

/--
The closed-form prefix state obeys the literal one-toppling transition.

This is the bridge between the counting formula and operational sandpile
semantics.
-/
theorem stateAfter_insert
    {S P : Finset α} {t x : α} (hx : x ∉ P) :
    stateAfter adj S (insert x P) t =
      topple adj (stateAfter adj S P t) x := by
  funext y
  unfold stateAfter topple
  rw [neighborCount_insert adj hx]
  by_cases hyx : y = x
  · subst y
    by_cases hloop : adj x x <;>
      simp [hx, hloop, Int.natCast_add] <;>
        omega
  · by_cases hyP : y ∈ P <;>
      by_cases hayx : adj y x <;>
        simp [hyx, hyP, hayx, Int.natCast_add] <;>
          omega

/--
The rooted enumeration is a legal once-each schedule.

The trigger is initially at height four.  Every later vertex is initially at
height three, has not toppled yet, and has received at least one grain from
an earlier adjacent vertex.
-/
theorem rootedOrder_legal
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order) :
    LegalSchedule adj S t order := by
  intro pre x suffix hsplit
  obtain ⟨hxPrefix, hroot | hpred⟩ :=
    cert.rooted pre x suffix hsplit
  · obtain ⟨hxt, hpre⟩ := hroot
    subst x
    subst pre
    simp [stateAfter, initialHeight, cert.trigger_mem, neighborCount]
  · obtain ⟨y, hyPrefix, hxy⟩ := hpred
    have hxOrder : x ∈ order := by
      rw [hsplit]
      simp
    have hxFinset : x ∈ order.toFinset := by
      simpa using hxOrder
    have hxS : x ∈ S := by
      rw [← cert.covers]
      exact hxFinset
    have hxNotPrefix : x ∉ pre.toFinset := by
      simpa using hxPrefix
    have hyFinset : y ∈ pre.toFinset := by
      simpa using hyPrefix
    have hpositive : 0 < neighborCount adj pre.toFinset x :=
      neighborCount_pos_of_mem adj hyFinset hxy
    by_cases hxt : x = t
    · subst x
      simp [stateAfter, initialHeight, hxS, hxNotPrefix] <;> omega
    · simp [stateAfter, initialHeight, hxS, hxNotPrefix, hxt] <;> omega

/--
The prefix formula composes into an actual step-by-step toppling execution.
-/
theorem rootedOrder_operational
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order) :
    OperationalSchedule adj S t order := by
  constructor
  · funext x
    simp [stateAfter, neighborCount]
  · intro pre x suffix hsplit
    have hxPrefix : x ∉ pre :=
      (cert.rooted pre x suffix hsplit).1
    have hxFinset : x ∉ pre.toFinset := by
      simpa using hxPrefix
    simpa using
      (stateAfter_insert adj
        (S := S) (P := pre.toFinset) (t := t) (x := x) hxFinset)

omit [DecidableRel adj] in
/--
The rooted enumeration implies the only lower-degree fact needed for final
nonnegativity: every non-trigger active vertex has an active neighbor.
-/
theorem RootedOrder.internalSupport
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order)
    {x : α} (hxS : x ∈ S) (hxt : x ≠ t) :
    ∃ y, y ∈ S ∧ adj x y := by
  have hxFinset : x ∈ order.toFinset := by
    rw [cert.covers]
    exact hxS
  have hxOrder : x ∈ order := by
    simpa using hxFinset
  obtain ⟨pre, suffix, hsplit⟩ :=
    exists_eq_append_cons_of_mem hxOrder
  obtain ⟨_, hroot | hpred⟩ :=
    cert.rooted pre x suffix hsplit
  · exact False.elim (hxt hroot.1)
  · obtain ⟨y, hyPrefix, hxy⟩ := hpred
    refine ⟨y, ?_, hxy⟩
    have hyOrder : y ∈ order := by
      rw [hsplit]
      exact List.mem_append_left (x :: suffix) hyPrefix
    have hyFinset : y ∈ order.toFinset := by
      simpa using hyOrder
    rw [cert.covers] at hyFinset
    exact hyFinset

/--
Arithmetic stability lemma for the once-each final state.

`internalDegreeFour` is the finite-graph form of ambient maximum degree four.
-/
theorem finalHeight_stable
    {S : Finset α} {t : α}
    (htS : t ∈ S)
    (internalDegreeFour :
      ∀ x, neighborCount adj S x ≤ 4)
    (triggerDegreeThree :
      neighborCount adj S t ≤ 3)
    (exteriorDegreeThree :
      ∀ x, x ∉ S → neighborCount adj S x ≤ 3)
    (internalSupport :
      ∀ x, x ∈ S → x ≠ t → ∃ y, y ∈ S ∧ adj x y) :
    Stable (finalHeight adj S t) := by
  intro x
  by_cases hxS : x ∈ S
  · by_cases hxt : x = t
    · subst x
      have hupper := triggerDegreeThree
      simp [finalHeight, stateAfter, initialHeight, htS] <;> omega
    · obtain ⟨y, hyS, hxy⟩ := internalSupport x hxS hxt
      have hlower : 0 < neighborCount adj S x :=
        neighborCount_pos_of_mem adj hyS hxy
      have hupper := internalDegreeFour x
      simp [finalHeight, stateAfter, initialHeight, hxS, hxt] <;> omega
  · have hxt : x ≠ t := by
      intro h
      apply hxS
      simpa [h] using htS
    have hupper := exteriorDegreeThree x hxS
    simp [finalHeight, stateAfter, initialHeight, hxS, hxt] <;> omega

/--
Exact characterization of stability after the once-each execution.

Under the automatic internal conditions supplied by a rooted degree-four
active set, the trigger and exterior upper bounds are not merely sufficient:
they are necessary, because their final heights are exactly their active
neighbor counts.
-/
theorem finalHeight_stable_iff
    {S : Finset α} {t : α}
    (htS : t ∈ S)
    (internalDegreeFour :
      ∀ x, neighborCount adj S x ≤ 4)
    (internalSupport :
      ∀ x, x ∈ S → x ≠ t → ∃ y, y ∈ S ∧ adj x y) :
    Stable (finalHeight adj S t) ↔
      neighborCount adj S t ≤ 3 ∧
        ∀ x, x ∉ S → neighborCount adj S x ≤ 3 := by
  constructor
  · intro stable
    constructor
    · have hupper := (stable t).2
      simp [finalHeight, stateAfter, initialHeight, htS] at hupper
      omega
    · intro x hxS
      have hxt : x ≠ t := by
        intro h
        apply hxS
        simpa [h] using htS
      have hupper := (stable x).2
      simp [finalHeight, stateAfter, initialHeight, hxS, hxt] at hupper
      omega
  · rintro ⟨triggerDegreeThree, exteriorDegreeThree⟩
    exact finalHeight_stable adj htS internalDegreeFour
      triggerDegreeThree exteriorDegreeThree internalSupport

/--
Exact finite-active-set kernel.

Every rooted order is an operational and legal once-each execution. Subject
only to ambient degree four, its endpoint is stable exactly when the trigger
and exterior degree bounds hold.
-/
theorem unitTopplingLoad_characterization
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order)
    (internalDegreeFour :
      ∀ x, neighborCount adj S x ≤ 4) :
    OperationalSchedule adj S t order ∧
      LegalSchedule adj S t order ∧
      (Stable (finalHeight adj S t) ↔
        neighborCount adj S t ≤ 3 ∧
          ∀ x, x ∉ S → neighborCount adj S x ≤ 3) := by
  refine ⟨rootedOrder_operational adj cert, rootedOrder_legal adj cert, ?_⟩
  exact finalHeight_stable_iff adj cert.trigger_mem internalDegreeFour
    (fun x hxS hxt =>
      RootedOrder.internalSupport adj cert hxS hxt)

/--
Finite unit-toppling load theorem with an explicit connectedness witness.

The schedule contains every active vertex exactly once by `cert.nodup` and
`cert.covers`; it is operational and legal; and its endpoint is stable.
-/
theorem unitTopplingLoad
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order)
    (internalDegreeFour :
      ∀ x, neighborCount adj S x ≤ 4)
    (triggerDegreeThree :
      neighborCount adj S t ≤ 3)
    (exteriorDegreeThree :
      ∀ x, x ∉ S → neighborCount adj S x ≤ 3) :
    OperationalSchedule adj S t order ∧
      LegalSchedule adj S t order ∧
      Stable (finalHeight adj S t) := by
  obtain ⟨operational, legal, characterization⟩ :=
    unitTopplingLoad_characterization adj cert internalDegreeFour
  exact ⟨operational, legal,
    characterization.mpr ⟨triggerDegreeThree, exteriorDegreeThree⟩⟩

/--
Existential form: constructive connectedness supplies an explicit legal
once-each schedule whose final state is stable.
-/
theorem unitTopplingLoad_of_rootConnected
    {S : Finset α} {t : α}
    (connected : RootConnected adj S t)
    (internalDegreeFour :
      ∀ x, neighborCount adj S x ≤ 4)
    (triggerDegreeThree :
      neighborCount adj S t ≤ 3)
    (exteriorDegreeThree :
      ∀ x, x ∉ S → neighborCount adj S x ≤ 3) :
    ∃ order : List α,
      order.Nodup ∧
      order.toFinset = S ∧
      OperationalSchedule adj S t order ∧
      LegalSchedule adj S t order ∧
      Stable (finalHeight adj S t) := by
  obtain ⟨order, cert⟩ := connected
  obtain ⟨operational, legal, stable⟩ :=
    unitTopplingLoad adj cert
      internalDegreeFour triggerDegreeThree exteriorDegreeThree
  exact ⟨order, cert.nodup, cert.covers, operational, legal, stable⟩

/--
Requested finite-graph form, with ambient maximum degree at most four.

The active-set degree bound needed by the core theorem follows by restricting
the ambient neighbor set to `S`.
-/
theorem unitTopplingLoad_of_rootConnected_maxDegreeFour
    [Fintype α]
    {S : Finset α} {t : α}
    (connected : RootConnected adj S t)
    (maxDegreeFour :
      ∀ x, neighborCount adj Finset.univ x ≤ 4)
    (triggerDegreeThree :
      neighborCount adj S t ≤ 3)
    (exteriorDegreeThree :
      ∀ x, x ∉ S → neighborCount adj S x ≤ 3) :
    ∃ order : List α,
      order.Nodup ∧
      order.toFinset = S ∧
      OperationalSchedule adj S t order ∧
      LegalSchedule adj S t order ∧
      Stable (finalHeight adj S t) := by
  exact unitTopplingLoad_of_rootConnected adj connected
    (fun x =>
      le_trans (neighborCount_le_univ adj S x) (maxDegreeFour x))
    triggerDegreeThree exteriorDegreeThree

/--
After the full schedule, the prefix-state formula is exactly `finalHeight`.
-/
theorem stateAfter_fullOrder
    {S : Finset α} {t : α} {order : List α}
    (cert : RootedOrder adj S t order) :
    ∀ x,
      stateAfter adj S order.toFinset t x =
        finalHeight adj S t x := by
  intro x
  rw [cert.covers]
  rfl

end Sandpile.UnitTopplingLoad
