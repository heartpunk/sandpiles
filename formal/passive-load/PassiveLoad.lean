import Std

/-!
An operational maximum principle for passive sandpile loads.

The ambient vertex type is unrestricted. A legal execution is a finite list
of actual unit topplings encoded inductively, and heights are reconstructed
from the four incoming neighbor counts. There is no stabilization axiom.
-/

namespace Sandpile

structure Grid (V : Type) where
  north : V → V
  south : V → V
  east : V → V
  west : V → V

def Grid.Adj (g : Grid V) (x y : V) : Prop :=
  y = g.north x ∨ y = g.south x ∨ y = g.east x ∨ y = g.west x

def height (g : Grid V) (initial added count : V → Nat) (x : V) : Int :=
  (initial x : Int) + (added x : Int) +
  (count (g.north x) : Int) + (count (g.south x) : Int) +
  (count (g.east x) : Int) + (count (g.west x) : Int) - 4 * (count x : Int)

def bump [DecidableEq V] (count : V → Nat) (x : V) : V → Nat :=
  fun y => if y = x then count y + 1 else count y

inductive Execution [DecidableEq V] (g : Grid V) (initial added : V → Nat) :
    (V → Nat) → Prop where
  | empty : Execution g initial added (fun _ => 0)
  | step {count : V → Nat} (prior : Execution g initial added count)
      (x : V) (legal : 4 ≤ height g initial added count x) :
      Execution g initial added (bump count x)

def BoundaryBound (g : Grid V) (load : V → Prop) (count : V → Nat)
    (cap : Nat) : Prop :=
  ∀ x, load x → ∀ y, g.Adj x y → ¬ load y → count y ≤ cap

theorem le_bump [DecidableEq V] (count : V → Nat) (x y : V) :
    count y ≤ bump count x y := by
  simp only [bump]
  split <;> omega

/-- A stable, source-free load never exceeds the final count at its boundary.
    This holds for every finite legal prefix, whether or not it is stable. -/
theorem passive_bound [DecidableEq V] (g : Grid V)
    (initial added count : V → Nat) (load : V → Prop)
    (stable : ∀ x, load x → initial x ≤ 3)
    (source_free : ∀ x, load x → added x = 0)
    (run : Execution g initial added count) :
    ∀ cap, BoundaryBound g load count cap → ∀ x, load x → count x ≤ cap := by
  induction run with
  | empty =>
      intro cap _ x _
      exact Nat.zero_le cap
  | @step count prior v legal ih =>
      intro cap boundary x hx
      have before : BoundaryBound g load count cap := by
        intro z hz y adjacent outside
        exact Nat.le_trans (le_bump count v y) (boundary z hz y adjacent outside)
      have previous := ih cap before
      by_cases same : x = v
      · subst x
        have local_bound : ∀ y, g.Adj v y → count y ≤ cap := by
          intro y adjacent
          by_cases inside : load y
          · exact previous y inside
          · exact before v hx y adjacent inside
        have hn := local_bound (g.north v) (Or.inl rfl)
        have hs := local_bound (g.south v) (Or.inr (Or.inl rfl))
        have he := local_bound (g.east v) (Or.inr (Or.inr (Or.inl rfl)))
        have hw := local_bound (g.west v) (Or.inr (Or.inr (Or.inr rfl)))
        have hv := previous v hx
        have hstable := stable v hx
        have hsource := source_free v hx
        simp [height, hsource] at legal
        simp [bump]
        omega
      · simpa only [bump, if_neg same] using previous x hx

/-- In particular, preserving a one-toppling interface precludes a repeated
    toppling anywhere in a passive load, irrespective of its size or shape. -/
theorem one_toppling_interface [DecidableEq V] (g : Grid V)
    (initial added count : V → Nat) (load : V → Prop)
    (stable : ∀ x, load x → initial x ≤ 3)
    (source_free : ∀ x, load x → added x = 0)
    (run : Execution g initial added count)
    (boundary : BoundaryBound g load count 1) :
    ∀ x, load x → count x ≤ 1 :=
  passive_bound g initial added count load stable source_free run 1 boundary

def incoming (g : Grid V) (count : V → Nat) (x : V) : Nat :=
  count (g.north x) + count (g.south x) +
  count (g.east x) + count (g.west x)

/-- Even aggregating all four incoming edges cannot deliver more than four
    times the interface cap to a passive target. -/
theorem incoming_bound [DecidableEq V] (g : Grid V)
    (initial added count : V → Nat) (load : V → Prop)
    (stable : ∀ x, load x → initial x ≤ 3)
    (source_free : ∀ x, load x → added x = 0)
    (run : Execution g initial added count)
    (cap : Nat) (boundary : BoundaryBound g load count cap)
    (target : V) (inside : load target) : incoming g count target ≤ 4 * cap := by
  have bounded := passive_bound g initial added count load stable source_free run cap boundary
  have local_bound : ∀ y, g.Adj target y → count y ≤ cap := by
    intro y adjacent
    by_cases hy : load y
    · exact bounded y hy
    · exact boundary target inside y adjacent hy
  have hn := local_bound (g.north target) (Or.inl rfl)
  have hs := local_bound (g.south target) (Or.inr (Or.inl rfl))
  have he := local_bound (g.east target) (Or.inr (Or.inr (Or.inl rfl)))
  have hw := local_bound (g.west target) (Or.inr (Or.inr (Or.inr rfl)))
  simp only [incoming]
  omega

/-- Literal delivery of a 71-grain packet requires at least an 18-toppling
    boundary allowance. This is a necessary condition, not a construction. -/
theorem packet71_requires_cap18 [DecidableEq V] (g : Grid V)
    (initial added count : V → Nat) (load : V → Prop)
    (stable : ∀ x, load x → initial x ≤ 3)
    (source_free : ∀ x, load x → added x = 0)
    (run : Execution g initial added count)
    (cap : Nat) (boundary : BoundaryBound g load count cap)
    (target : V) (inside : load target)
    (packet : 71 ≤ incoming g count target) : 18 ≤ cap := by
  have ceiling := incoming_bound g initial added count load stable source_free run
    cap boundary target inside
  omega

/-- The actual infinite, sinkless square lattice is an instance of the model. -/
def squareGrid : Grid (Int × Int) where
  north := fun (r, c) => (r - 1, c)
  south := fun (r, c) => (r + 1, c)
  east := fun (r, c) => (r, c + 1)
  west := fun (r, c) => (r, c - 1)

#print axioms passive_bound
#print axioms one_toppling_interface
#print axioms incoming_bound
#print axioms packet71_requires_cap18

end Sandpile
