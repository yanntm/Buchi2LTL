# Spot Temporal Logic — Simplifications for Eventual & Universal Formulas
**Source:** Spot 2.15.1 documentation, page 27 (section 5.4.2)

## Notation

| Symbol     | Meaning                                      |
|------------|----------------------------------------------|
| \(f, f_i, g, g_i\) | Any PSL formula                              |
| \(e, e_i\) | Pure eventuality                             |
| \(u, u_i\) | Purely universal formula                     |
| \(q, q_i\) | Pure eventuality **and** purely universal    |

**Legend**  
- `≡` = always applied  
- `‹”` = may increase formula size (disabled by `reduce_size_strictly`)  
- `Ĳ”` = applied only when `favor_event_univ = true`  
- `Ź”` = applied only when `favor_event_univ = false`

---

## Rules

### Basic absorption & distribution

- \( Fe \equiv e \)
- \( fUe \equiv e \)
- \( eMg \equiv e \land g \)
- \( u_1Mu_2 \quad \mathrel{\text{‹”}} \quad (Fu_1) \land u_2 \)
- \( F(u \lor q) \lor q \quad \mathrel{\text{Ź”}} \quad F(u \lor q) \)
- \( fU(g \lor e) \quad \mathrel{\text{Ĳ”}} \quad (fUg) \lor e \)
- \( fM(g \land u) \quad \mathrel{\text{Ĳ”}} \quad (fMg) \land u \)
- \( qUXf \equiv X(qUf) \)
- \( fU(g \land q) \quad \mathrel{\text{Ĳ”}} \quad (fUg) \land q \)
- \( (f \land q)Mg \quad \mathrel{\text{Ĳ”}} \quad (fMg) \land q \)

### Universal-side rules

- \( Gu \equiv u \)
- \( uWg \equiv u \lor g \)
- \( fRu \equiv u \)
- \( e_1We_2 \quad \mathrel{\text{‹”}} \quad (Ge_1) \lor e_2 \)
- \( G(e \land q) \equiv G(e \land q) \)
- \( fW(g \lor e) \quad \mathrel{\text{Ĳ”}} \quad (fWg) \lor e \)
- \( fR(g \land u) \quad \mathrel{\text{Ĳ”}} \quad (fRg) \land u \)
- \( qRXf \equiv X(qRf) \)

### X / q interaction (key for leading X removal)

- \( Xq \equiv q \)
- \( q \land Xf \quad \mathrel{\text{Ź”}} \quad X(q \land f) \)
- \( q \lor Xf \quad \mathrel{\text{Ź”}} \quad X(q \lor f) \)
- \( X(q \land f) \quad \mathrel{\text{Ĳ”}} \quad q \land Xf \)
- \( X(q \lor f) \quad \mathrel{\text{Ĳ”}} \quad q \lor Xf \)

### Lifting inside G (drop X when subformula is eventual)

- \( G(f_1 \land \dots \land f_n \land Xe_1 \land \dots \land Xe_p) \equiv G(f_1 \land \dots \land f_n \land e_1 \land \dots \land e_p) \)
- \( G(f_1 \land \dots \land f_n \land F(g_1 \land \dots \land g_p) \land Xe_1 \land \dots \land Xe_m) \equiv G(f_1 \land \dots \land f_n \land F(g_1 \land \dots \land g_p) \land e_1 \land \dots \land e_m) \)

### Lifting inside F (drop X when subformula is universal)

- \( F(f_1 \lor \dots \lor f_n \lor Xu_1 \lor \dots \lor Xu_p) \equiv F(f_1 \lor \dots \lor f_n \lor u_1 \lor \dots \lor u_p) \)
- \( F(f_1 \lor \dots \lor f_n \lor G(g_1 \lor \dots \lor g_p) \lor Xu_1 \lor \dots \lor Xu_m) \equiv F(f_1 \lor \dots \lor f_n \lor G(g_1 \lor \dots \lor g_p) \lor u_1 \lor \dots \lor u_m) \)

### G/F distribution with q

- \( G(f_1 \lor \dots \lor f_n \lor q_1 \lor \dots \lor q_p) \equiv G(f_1 \lor \dots \lor f_n) \lor q_1 \lor \dots \lor q_p \)
- \( F(f_1 \land \dots \land f_n \land q_1 \land \dots \land q_p) \quad \mathrel{\text{Ĳ”}} \quad F(f_1 \land \dots \land f_n) \land q_1 \land \dots \land q_p \)
- \( G(f_1 \land \dots \land f_n \land q_1 \land \dots \land q_p) \quad \mathrel{\text{Ĳ”}} \quad G(f_1 \land \dots \land f_n) \land q_1 \land \dots \land q_p \)
- \( GF(f_1 \land \dots \land f_n \land q_1 \land \dots \land q_p) \equiv G(F(f_1 \land \dots \land f_n) \land q_1 \land \dots \land q_p) \)

### Further G/F lifting with eventual/universal subformulas

- \( G(f_1 \land \dots \land f_n \land e_1 \land \dots \land e_m \land G(e_{m+1}) \land \dots \land G(e_p)) \quad \mathrel{\text{Ĳ”}} \quad G(f_1 \land \dots \land f_n) \land G(e_1 \land \dots \land e_p) \)
- \( G(f_1 \land \dots \land f_n \land G(g_1) \land \dots \land G(g_m)) \equiv G(f_1 \land \dots \land f_n \land g_1 \land \dots \land g_m) \)
- \( F(f_1 \lor \dots \lor f_n \lor u_1 \lor \dots \lor u_m \lor F(u_{m+1}) \lor \dots \lor F(u_p)) \quad \mathrel{\text{Ĳ”}} \quad F(f_1 \lor \dots \lor f_n) \lor F(u_1 \lor \dots \lor u_p) \)
- \( F(f_1 \lor \dots \lor f_n \lor F(g_1) \lor \dots \lor F(g_m)) \equiv F(f_1 \lor \dots \lor f_n \lor g_1 \lor \dots \lor g_m) \)
- \( G(Ff_1) \land \dots \land G(Ff_n) \land G(e_1) \land \dots \land G(e_p) \quad \mathrel{\text{Ĳ”}} \quad G(f_1 \land \dots \land f_n) \land G(e_1 \land \dots \land e_p) \)
- \( F(Gf_1) \lor \dots \lor F(Gf_n) \lor F(u_1) \lor \dots \lor F(u_p) \quad \mathrel{\text{Ĳ”}} \quad F(f_1 \lor \dots \lor f_n) \lor F(u_1 \lor \dots \lor u_p) \)

### Final absorption (only when no other terms in OR)

- \( F(f_1) \lor \dots \lor F(f_n) \lor q_1 \lor \dots \lor q_p \quad \mathrel{\text{Ź”}} \quad F(f_1 \lor \dots \lor f_n \lor q_1 \lor \dots \lor q_p) \)

---

**Note:** These rewritings are performed by `tl_simplifier` when the corresponding options are enabled.

