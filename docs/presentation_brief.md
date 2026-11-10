# Presentation brief: everything behind the SfN 2026 poster

For a person who has to understand, defend or present every panel of the poster "Axis-tuned units emerge in trained recurrent networks" without the author beside them. Every number here is read from the project's stored tables and notes as of 2026-11-10: the arm tables of experiments 2026-10-24 (inputs) and 2026-10-25 (sweeps), the effect-size and claims tables of 2026-10-27 and 2026-10-28, the criterion note under `results/sfn-2026/sfn_2026_criterion`, the rotation table of 2026-10-29, the dataset information notebook under `eda/sfn_2026_information`, and the configs and docstrings of `scripts/sfn_2026` and `scripts/axis_tuning_validator/sfn_2026_validation.py`. Where the record is silent or a point is unsettled, this brief says so rather than filling the gap.

Contents

1. The biology
2. The question, and why a latent-variable model
3. The data
4. The models
5. The criterion as ported
6. The null and the statistics
7. The figures, panel by panel
8. The six results
9. The two discriminating tests: arena and rotation
10. Discussion points and likely questions
11. Glossary

---

## 1. The biology

**The subiculum** is the main output structure of the hippocampal formation, sitting between CA1 and the entorhinal and retrosplenial cortices, with direct projections to anterior thalamus. Its neurons carry location, orientation and trajectory information in mixed forms, and it receives head-direction input (via presubiculum and anterior thalamus), spatial input (CA1 place cells, medial entorhinal cortex) and self-motion signals.

**Axis-tuned cells.** Olson, Tongprasearth and Nitz (2017, *Nature Neuroscience* 20, "Subiculum neurons map the current axis of travel") recorded dorsal subiculum while rats ran a spatial working-memory task on a triple-T maze: from a start corridor the animal turns left or right at three successive T junctions toward one of four reward arms, then returns to the start around the maze's perimeter. They described cells that fire when the animal travels along a particular axis, north-south say, in *both* directions along it, on *every* corridor with that orientation, regardless of where the corridor lies. Three properties define the type:

1. **Two opposite peaks** in the tuning curve by direction of travel, 180° apart.
2. **Spatial independence**: the firing is spread along the length of each corridor rather than confined to one place. The paper quantified it as the fraction of position bins traversed in a peak direction in which the cell was active, 74% on average.
3. **No axis tuning in the open arena.** The same cells recorded during open-field foraging did not pass the same shape criteria. Their peak-to-minimum ratio fell (track mean 4.65, s.d. 2.23, after removing one outlier of 90.4; arena significantly lower, roughly 1.5 to 2 in the paper's box plot, P = 1.79 × 10⁻¹¹ over 47 cells) and their peaks broadened (circular variance about 0.27 rad, roughly 16°, on the track against about 23° in the arena). Spatial independence did not change (P = 0.07).

The paper's conclusion from the third property is that axis cells are "clearly distinguishable from head direction neurons, whose activity maps only a single orientation and whose tuning is present during foraging in open arenas". That sentence is a population contrast, not a rule, and it matters later (section 5 and 9).

**The rotation experiment.** In a subset of sessions the maze was turned by 90° in the room. For 26 axis cells the tuning curve after the turn correlated with the original at 0.76 ± 0.16 when both were read in room coordinates, and at −0.41 ± 0.22 when the turned curve was read in track coordinates (turned back by 90°). The cells kept their room direction: they are anchored to the room, not to the apparatus.

**Why it is interesting.** An axis code is neither a place code nor a head-direction code. It is a representation of the orientation of a path segment, abstracted from position and from the two directions of travel along it. The poster's introduction frames this as a schema-level code: a way of composing low-level inputs into a geometry-dependent relational code that is place unspecific.

## 2. The question, and why a latent-variable model

**The question.** Can axis tuning emerge, without being imposed, in the hidden state of a recurrent network trained on the rat's own trajectories to do something the subiculum plausibly does, predict where the animal will be a moment from now? And if it does, which inputs does it need, and does it behave like the recorded cells off the track?

**Why a trained recurrent network.** The claim being tested is one of sufficiency: given head direction, place and angular velocity as inputs, and a prediction objective, does a latent axis code arise? A hand-built model could show that an axis cell *can* be wired from these inputs; a trained one asks whether a generic learner *does* build it. The hidden units are the latent variables; no unit is told to be direction tuned. The two architectures, a step RNN and a GRU, are two generic learners, not models of subicular circuitry.

**What would count as an answer.** The poster scores every hidden unit with the paper's criterion and compares the count per trained network with the count in untrained networks of the same type and inputs. A positive answer is "more than chance, and the extra units behave like the recorded cells in the arena and under rotation". A negative answer is "no more than chance" or "more than chance, but the units are something else", and both are reported.

**Three hypotheses the design keeps apart.**

- The inputs alone produce axis-shaped units, with no learning (the "apparent tuning" case the project brief says validation must rule out).
- Learning the prediction task produces them.
- Units that pass the criterion are head-direction cells that the corridor geometry folds into two peaks.

The input-subset arms test the first two; the arena contrast and the rotation test address the third.

## 3. The data

**Source.** The lab's recordings behind Olson et al.: overhead video tracking of two head-mounted LEDs at 60 Hz, with the lab's own segmentation of each session into arena, track and maze-rotation epochs and its hand-marked outbound and return runs. Three rats, NS14, NS15 and NS16.

**Pipeline (Fig. 2).** Three stages, all in this repository: (1) *convert* the MATLAB files once into typed tables, resampling nothing, flagging every anomaly; (2) *build blocks*: register pixels into room metres from the maze's published geometry (room 1.8 m square; outbound segments 0.51, 0.36, 0.31 and 0.22 m; arena diameter 0.6 m), compute heading, speed and turn rate, cut the tracking into continuous stretches, label every frame; (3) *review* each block by eye and record a verdict beside the data.

**Cutting rules.** A cut happens at a recording pause (clock step over 0.5 s), a position jump over 40 px in one frame, or an LED loss longer than 180 frames (3 s). Five seconds are trimmed beside each pause, jump or epoch edge, and any piece under 10 s is dropped. Dwells at reward sites are never cut. The cutting kept 98.8% of the track time and 97.1% of the arena time that survived selection.

**What the build holds.** The build `2026-11-03T022629Z_sfn-2026-baseline` considered 81 sessions (82 selected, one failed to load), of which 50 yielded at least one block, on 45 distinct recording dates. It holds 67 blocks, 28 on the track and 39 in the arena, 10.2 hours of continuous trajectory (6.25 h track, 3.98 h arena), 736 k frames at 20 Hz. Only baseline epochs are built; the lab's rotated-maze epochs were excluded by decision and kept for a later geometry test. Per rat: NS14 12 sessions and 16 blocks, NS15 18 and 24, NS16 20 and 27. On the track, frames are 14.7% outbound run, 24.9% return run and 60.4% dwell; the median run lasts about 3 s and the median time between turn onsets is about 0.95 s.

**Frame rate.** The models run at 20 Hz: the adapter keeps every third 60 Hz frame, thinning the stored speed and turn-rate values rather than recomputing them.

**Split.** Recording dates, not blocks, are assigned to train, validation and test in the proportions 0.67 / 0.11 / 0.22 with a fixed seed, so no day's behaviour appears in two splits. Every block of a date goes to that date's split. The validator scores networks on the test split only.

**Immutability.** Each build is timestamped and content-hashed (84eab93d…), the hash is pinned in every experiment's `experiment.yaml`, and the build protocol is snapshotted in the repository. Nothing downstream writes into the dataset.

## 4. The models

**Inputs are populations of tuning-curve cells**, each emitting rates in [0, 1] with peak 1, built per block from the behaviour:

- **Head direction, H**: 40 cells with evenly spaced preferred directions and von Mises tuning, widths drawn lognormally around a median full width at half maximum of 40° (spread 0.35), after Duszkiewicz et al. 2024.
- **Place, P**: 100 Gaussian place fields of standard deviation 0.15 m, centres on a jittered grid that spans the room evenly at every count (RatInABox's default recipe), peak 1.
- **Angular velocity, A**: 12 cells after Spalla, Treves and Boccara 2022: 3 driven by turning one way, 3 the other way, 6 by turning speed regardless of sign, each a baseline between 0.1 and 0.3 plus a linear ramp reaching 1 at 3 rad/s. This population is marked provisional in the record.

The seven non-empty subsets of {H, P, A} are the input arms. Removing a population is a config edit; the other populations' draws are unchanged.

**Two cell types.**

- **Step RNN** (the poster says "vanilla RNN"): h_t = tanh(relu(W_in x_t + b + W_rec h_{t−1})) from h_0 = 0, with a linear readout. Weights uniform in ±1/√hidden. Hidden states are non-negative by construction.
- **GRU**: one PyTorch GRU layer with its default initialisation and a linear readout. Hidden states lie in (−1, 1); for scoring they are clipped at 0 to make rates, a provisional choice recorded in the plan.

Hidden size 128 in the base; 32, 64 and 256 as sweep arms.

**Task.** Predict the animal's (x, y) position 1 s ahead, standardised with the training split's mean and s.d., from the input populations over the preceding 0.5 s of history. Training windows are cut every 0.25 s anywhere in a track block where position, heading and turn rate are all finite, dwell and turn-arounds included; the first 0.25 s of each window carries no loss (burn-in). Arena blocks are never trained on. History 0.5 s was chosen so that one window holds about one turn and the network cannot read the turn sequence off its input; 1 s is a sweep arm. Horizons 2, 5 and 10 s are sweep arms.

**Optimisation.** Adam at 1e-3, batch 128, gradient norm clipped at 1.0, up to 50 epochs, early stopping after 5 epochs without improvement on the validation loss, the best epoch's weights kept. Ten network seeds per arm; the input-population seed is fixed. 140 networks in the inputs experiment, 300 in the sweeps.

**The persistence baseline.** Persistence predicts that the animal will be where it is now. Its loss is the same masked mean squared error, with the current position in place of the network's output, on the same windows. The *fit ratio* reported everywhere is the network's best validation loss divided by this baseline: below 1 the network is predicting movement, above 1 it is doing worse than standing still. Arms with place input reach ratios of 0.16 to 0.22. Arms without it, H, A and HA, sit at 3.3 to 5.2, because those networks never receive position: head direction and turning do not tell you where you are, so they cannot even reproduce persistence. For them the baseline is a weak yardstick. Whether a head-only network learned what heading allows, for example the mean position per heading, has not been tested; a mean-position baseline per split was proposed and not run. When the poster says these networks "did not learn the task", read it as "could not beat persistence", and expect the question.

**Validation.** The validator runs each trained network from a zero hidden state over every whole test block and reads the hidden unit time series; windows feed only the training and validation loss.

## 5. The criterion as ported

The validator (`sfn_2026_validation.py`, rule version `sfn-2026-v3`) is model independent: it takes an activity matrix (frames × units) and the behaviour table. It ports the paper's criteria as the previous repository's version-3 implementation had them; the plan documents each deviation.

**Tuning curves.** On the track, *run frames* are frames in an outbound or return run with speed above 0.03 m/s; the angle is the *direction of travel*, the direction of the change in position. In the arena, frames are foraging frames with speed above 0.1 m/s and the angle is *head direction*. Activity is averaged in 36 bins of 10°. Every travel bin is occupied on the real test split (checked at build time), so the mixture never sees zero-filled bins.

**Shape test, the paper's model.** A mixture of von Mises components (the circular analogue of Gaussians) is fitted by expectation-maximisation to the tuning curve, read as weights on the bin centres, for orders 0 to 8, with 10 random starts and 50 iterations each, the concentration κ capped at 50. The fit is done on one half of the data and scored on the other: the run frames are split by traversal into a *fitted half* (`track_half`, drawn with a fixed seed) and a held-out half; arena frames are split by 30 s chunks. The chosen order is the last one at which adding a component still cuts the held-out squared error by at least 20% and the error ratio stays at most 0.5. A unit has an **axis shape** when the chosen order is 2, the two component means are opposite within 20°, the data at the model's peaks is at least 0.1, and the peak data is more than twice the data at the troughs. A trough observed at exactly zero still passes (the ratio is infinite); a trough bin with no frames fails (the ratio is undefined). This last rule fixes a defect in the ported code and never triggers on the real data.

**Spatial independence.** At each of the two peak directions, take the frames whose travel direction is within ±5° of it, bin their positions into 2 cm bins along the room axes, keep bins holding at least 10 such frames, and compute the fraction of those bins in which the unit's mean activity is at least half its mean over all those frames. The rule passes when that fraction is at least 0.5 at *both* peaks. It is the paper's statistic with the paper's 50% activity threshold.

**Arena release.** The same shape test is run on the arena head-direction curve. A unit is an axis unit only if the arena curve does *not* have an axis shape. This is exactly the paper's formal arena test ("the same methodology and criteria"). What it does not carry is the paper's prose distinction from head-direction cells: a unit sharply tuned to one heading in the arena has order 1 there, fails the axis shape, and passes the release. Section 9 shows this matters.

**The verdict.** `axis_unit` = axis shape AND spatial independence AND NOT arena axis. This is the headline count (plan decision 29). The previous repository's headline added a cardinal restriction (first peak within 25° of east, north, west or south); that is now a reported fraction, not a rule, because it is an expectation about the track and not a rule of the paper, and nearly all travel on the triple-T is cardinal anyway.

**Kind labels, and why they are not used.** The validator also tries to say what each passing unit is made of: it fits a Fourier basis in angle on frames where heading and travel agree, predicts the divergent frames (heading and travel more than 45° apart) with travel and with heading as the angle, and asks whether position bins explain more than 10% of the residual variance. In every folder every passing unit, trained or untrained, with or without place input, came out "place-modulated" (8292 of 8299 null units, 330 of 330 trained units in the inputs experiment). A calibration control on synthetic behaviour (experiment 2026-10-26) found the test labels planted units correctly even when the divergent frames sit in one part of the room, so the label is not a simple artefact, but the trained units' statistical signature matches no planted kind. The decisive control, planting units on the real behaviour, has not been run. The poster therefore does not use the labels; the claims notebook compares only their raw statistics. If asked what the units are, answer with the arena and rotation tests (section 9), not the kind labels.

## 6. The null and the statistics

**Why an untrained null.** A randomly initialised network fed head-direction cells already contains hidden units with two opposite peaks on the track, because random weights sum head-direction cells and the corridors constrain heading. The previous repository learned this the hard way: every early count was withdrawn against such a null. So before any trained network was scored, 100 untrained networks were drawn for each of the 36 combinations of cell type, hidden size and input set (3600 draws, seeds 10 000 upward so no draw coincides with a training seed), run over the same test blocks and scored by the same validator. The nulls are frozen in experiment 2026-10-23 and read by the others.

**Unit of analysis.** The count of axis units *per network*, not the unit. Units within a network share weights, inputs and the same behaviour, so they are not independent observations; networks with different seeds are. Every test compares 10 trained counts with 100 untrained counts.

**The Mann-Whitney U test, from first principles.** Pool the 110 counts and rank them from smallest to largest, giving tied values the average of the ranks they span. Sum the ranks of the 10 trained counts. If training made no difference, the trained counts are an arbitrary subset of the pool and their rank sum is what you would get by picking 10 of the 110 at random. U is that rank sum minus its minimum possible value, so U counts how many (trained, untrained) pairs have the trained count larger (ties count a half). The test asks how often a random relabelling gives a rank sum at least as large as the observed one. It uses only order, so it needs no assumption about the shape of the count distributions, which are small integers with many zeros.

**One-sided.** The claim pre-registered in the plan (decision 30) is "trained networks hold *more* axis units than untrained ones", so the p is the probability of a rank sum at least as large under relabelling. The lower tail, "fewer than chance", is reported in the 2026-10-27 notebook as a post hoc description, not a test.

**Why the asymptotic version failed.** scipy's Mann-Whitney switches to a normal approximation whenever ties are present, and with counts of 0, 1 and 2 the ties are massive. On 2026-11-09 the step RNN A arm, one unit in one network against 100 untrained zeros, read p = 0.0009 under that approximation; the exact answer is that the one non-zero count lands among the 10 trained in 10 of 110 relabellings, p = 0.09. The validator now computes the **permutation p**: the pooled counts are ranked once, 100 000 random relabellings are drawn with a fixed seed, and p = (relabellings at least as extreme + 1) / (100 001). The floor is therefore 1e-5; a quoted "p < 1e-5" means no relabelling reached the observed statistic. Only the step RNN A claim changed; the earlier tables are kept beside the new ones as `arms_asymptotic_2026-11-09.csv`.

**Level and multiplicity.** A claim is an arm test with p below 0.01. There are 44 tests (7 input arms plus 15 sweep arms, each in two cell types). Under a global null about 0.44 false claims are expected at that level across the set; the poster reports every test, claims and non-claims, on one axis (Fig. 6) rather than correcting and hiding the rest. The arms are not independent of one another (they share the dataset and the split, and the horizon and history arms share the base null set), so the count of arms below or above chance is a description, not a test.

**Effect size.** For every arm test, the trained mean minus the null mean, with a 95% percentile bootstrap interval (both groups resampled, 10 000 resamples, seed 0). The diamonds in Fig. 4 and the points in Fig. 6 are trained means; the error bars in Fig. 4 and Fig. 6 are the t-based 95% confidence interval of the mean over the 10 seeds.

**Robustness.** For each claim the arm test was recomputed leaving out each seed in turn. Every claim but one survives all ten leave-one-out tests at 0.01; GRU history 1 s survives 4 of 10 (largest p 0.019). Beside each claim the tables give the fraction of its 10 networks above the null's 95th percentile, a descriptive per-network view: 0.8 for GRU H, 0.5 to 0.6 for the place-only claims and hidden 256, 0.3 for 4 place cells, 0.2 for history 1 s, 0.1 for GRU HP.

**Fits of the null distributions.** Each set's 100 counts were fitted as Poisson and as negative binomial and compared by AIC; 33 of 36 are Poisson, A is constant at zero, one (HP step RNN) marginally negative binomial. A Poisson count is what results when each hidden unit passes independently with a small probability, so the sets differ in that probability (about zero without head-direction input, about 0.2% per unit with place input alone, 1 to 3.5% with head-direction input) rather than in the shape of chance. These fits describe chance; the arm test uses the raw draws.

## 7. The figures, panel by panel

**Figure 1, the apparatus.** The triple-T maze and the open arena in the room frame, from the lab's geometry. Note the maze's corridors run in only two orientations, along the room axes; this fact drives the discussion.

**Figure 2, the data pipeline.** The three stages of section 3 as a flow chart, from the lab's MATLAB files to immutable hashed block datasets, then the window construction: each window is 0.5 s of input history and a target 1 s ahead, cut every 0.25 s, split by recording day. The split and windows are made at load time, never written back.

**Figure 3, chance, "Untrained networks already contain axis units when they receive head direction".** Each row is one null set at 128 hidden units (the single and paired input sets) or the full set HPA at hidden sizes 32 to 256; left the step RNN, right the GRU. Each horizontal box is the median and quartiles of the 100 untrained counts, the whiskers the 5th and 95th percentiles, every draw a jittered point. The upper whisker end is the threshold a trained network of that set must beat to count as "above the null" in the descriptive per-network sense. Colour is the set's chance class: *zero* (vermilion) when no untrained network ever holds an axis unit (A alone), *rare* (green) when the mean is below 0.5 (P, PA), *expected* (blue) otherwise (every set containing H). Below, one representative set per class with its fitted probability mass function (pmf, the fitted probability of each count) as a line and the observed draw frequencies as dots. What it does not show: anything about trained networks.

**Figure 4, "counts against the null, and whether the networks learned".** Top: per input set, the null's fitted distribution in grey, its 95th percentile dashed, the ten trained seeds as points, their mean as a diamond with a 95% CI, and above each set the arm test's permutation p, bold with an asterisk when below 0.01 (the p values shown as "p = 1" are rounded; the exact values are 0.97 to 1.00). Colours are the chance classes of Fig. 3. Bottom: validation loss per epoch on a logarithmic axis, one mean line per input set, seeds faint, the persistence baseline as the grey dashed horizontal line. Within a class the sets are told apart by line style: H solid, HP dashed, HA dotted, HPA dash-dot in blue; P solid, PA dashed in green; A solid in vermilion. Read the two panels together: a set's count is only interpretable once you know whether its curve sits below or above the dashed line. Sets with place input drop to about a fifth of persistence within a few epochs; H, A and HA never fall below it.

**Figure 5, the six example units.** One block per unit, chosen by hand to span the kinds the criterion admits, not drawn at random. Each block:

- Top, on grey: the unit's activity along one test session's path on the track (colour is activity per frame, plasma colour map, zero to the unit's 99th percentile, one colour bar per block at the right), the same session with the track turned 90° clockwise about the room centre, and the same session in the arena.
- Bottom left polar plot: mean activity by direction of travel on the track (blue bars) over mean activity by head direction in the arena (grey bars). Gold dots sit at the two fitted peak directions on the blue bars, gold lines run from the centre through them. The grey circle is the unit's maximum mean activity over the three curves shown in the block, written as "max" at the corner, and both polar plots of a block share that radius so the blue histogram is drawn at one scale in both; the black circle is 1.25 times the max. The line above gives the peaks' separation and the track peak-to-trough ratio.
- Bottom middle polar plot: the turned track's tuning (light purple) over the original (blue), both in room coordinates. Purple dots and lines mark the peaks the validator fits to the turned curve, when it finds an axis shape there (two lines), a single peak (one line) or none (no mark). The line above gives r, the correlation between original and turned curves in the room frame. Purple over blue means the unit kept its room direction, as the recorded cells did; purple turned by a quarter turn would mean the tuning followed the track; a small round purple blob means the turn destroyed the tuning.
- Bottom right: the two tuning curves as lines, track blue and arena grey, with gold dots and vertical lines at the fitted peaks.

The six units, as on the poster: top left, corridor-wide north-south (step RNN, 5 s horizon arm, seed 0, unit 124; peaks 87° and −82°, ratio 3.6, room-frame r 0.89); top right, sharp bimodal from place input only (GRU P, seed 9, unit 88; peaks −89° and 90°, ratio 4.5, arena ratio 22.9, room-frame r −0.28, turned fit order 1); middle left, sharp bimodal from all inputs with 16 place cells (GRU, seed 9, unit 59; peaks 97° and −91°, ratio 6.8, room-frame r 0.34, turned fit order 0, so no purple mark); middle right, diagonal (step RNN, 1 s history arm, seed 4, unit 69; peaks 143° and −54°, ratio 6.6, room-frame r 0.10); bottom left, head direction only (GRU H, seed 1, unit 122; peaks −68° and 110°, ratio 3.4, room-frame r 0.58); bottom right, room anchored (GRU H, seed 9, unit 76; peaks −73° and 93°, ratio 5.3, arena ratio 93.8, room-frame r 0.97, still an axis unit when turned). Three of these come from arms that did not beat their null (5 s horizon, 16 place cells, 1 s history step RNN); they illustrate forms the criterion admits, not effects of training. Be aware that the top-right place-only unit has an unusually sharp arena curve (ratio 22.9) while place-only units as a population have an arena median of 2.9; it is an atypical exemplar for result 5.

**Figure 6, "trained count against chance, one point per arm test".** Every one of the 44 arm tests as a point: x is the null mean (chance), y is the trained mean with its 95% CI, the dashed diagonal is "trained equals chance". Colour is the chance class; a dark, thick edge in a darker shade of the class colour marks a claim (p < 0.01); a downward triangle marks an arm whose networks did not beat persistence. Points above the diagonal hold more axis units than chance, below fewer. The figure shows at a glance that chance is set by the inputs (the blue cloud sits far right of the green and vermilion ones), that most arms lie on or under the diagonal, and that the claims are the few points above it. It does not show significance by distance from the line: a point can sit above the diagonal with a wide interval and not be a claim.

## 8. The six results

Numbers are from the permutation arm tests. "Fit" is the median seed fit ratio to persistence.

**1. Head-direction input alone yields axis-shaped units, without learning the task (Fig. 4, 6).** GRU H: 7.1 axis units per network against 1.8 untrained, difference +5.3 (95% CI 4.0 to 6.6), p < 1e-5, 8 of 10 networks above the null's 95th percentile, fit 3.4. The step RNN with the same input: 3.8 against 2.7, p = 0.02, not a claim. This is the largest shift in the whole study and it comes from networks that never beat persistence, so it cannot be a consequence of learning position prediction. It is also cell-type specific. Caveat: "did not learn" means "did not beat persistence", a baseline a head-only network cannot in principle reach (section 4).

**2. Place input is enough to learn the task and yields a few axis units above chance (Fig. 4, 6).** Every set with place input reaches a fit of 0.16 to 0.22. Chance without head-direction input is near zero (0.28 to 0.35 per network). Training adds about one and a half units: GRU P 1.7 against 0.3 (+1.4, CI 0.5 to 2.3, p = 0.0003); step RNN P 1.8 against 0.3 (+1.5, CI 0.9 to 2.1, p < 1e-5); GRU PA 1.9 against 0.4 (+1.6, CI 0.9 to 2.2, p < 1e-5); step RNN PA 1.2 against 0.3 (p = 0.08, not a claim). Adding head direction to place raises chance to 3.6 and the trained GRU count to 5.2 (+1.6, CI 0.7 to 2.6, p = 0.002), but only one of its ten networks is above the null threshold. The full set HPA falls below its own null in both cell types: −1.3 (CI −2.3 to −0.3) for the GRU and −1.3 (−2.2 to −0.4) for the step RNN. Angular velocity alone: fit 5.2, no axis units in the GRU and one unit in one step RNN network (p = 0.09). On the poster's older wording: HP and HPA fit marginally *better* than P (0.17 against 0.19), so say "barely improves the fit", not "did not improve".

**3. Architecture and prediction horizon move the count at the margin (Fig. 6).** Of the 30 sweep arms around HPA, three GRU arms exceed their null: 256 hidden units, 6.8 against 3.2 (+3.6, CI 2.3 to 4.9, p < 1e-5); 1 s of input history, 4.9 against 3.2 (+1.7, CI 0.5 to 2.8, p = 0.006, and the one fragile claim: 4 of 10 leave-one-seed-out tests hold); four place cells, 3.6 against 1.5 (+2.1, CI 1.3 to 3.0, p < 1e-5, fit 0.99, at the persistence baseline). Every step RNN sweep arm sits at or below its null, 13 of 16 with the bootstrap interval wholly below zero, and the step RNN HPA arms have fewer axis-*shaped* units than their nulls already at the shape rule. Longer horizons lower the count as the fit worsens: at 5 s, 0.6 (GRU) and 0.7 (step RNN) per network against 3.2 and 3.8, fit 0.28. Place-field width (0.10, 0.30 m) and the other place counts (9 to 64) change nothing at 0.01.

**4. What the units look like (Fig. 5).** Passing units fire along whole corridors in both directions of their axis, independent of position, and satisfy the paper's three criteria. In the examples the peaks are 163° to 178° apart. Across the trained conditions the median track spatial independence is 70 to 86% (the paper's 74%) and the median track peak-to-trough ratio 2.6 to 4.7 (the paper's mean 4.65, s.d. 2.23); two thirds or more of the units of every condition fall within one paper s.d. of 4.65. The fitted peaks are about twice as broad as the paper's (circular standard deviations 26° to 45° against about 16°), which the criterion note attributes to 10° binning, the κ cap and noise-free rates; compare directions of change, not levels. The track statistics do not separate conditions and do not separate trained from untrained networks, as expected: the criterion requires them and the track geometry supplies the shape.

**5. The arena separates two kinds of unit (Fig. 5, grey curves; criterion notebook figure 02).** The paper's cells lose their tuning in the arena. The model's axis units split by input. Units from head-direction input go the other way: median arena ratio 10.0 against 3.6 on the track in the GRU (14 against 4.7 in the step RNN), the arena ratio higher than the track ratio in 10 of 10 GRU networks, with one arena peak in a third of the units, a two-component arena fit whose peaks are not opposite in half, and more than two peaks in the rest; none has the axis shape (certified in results/sfn-2026/sfn_2026_results, section 5). Units from place input broaden in the arena in every network (7 of 7 P, 9 of 10 PA GRU networks have broader arena peaks), three quarters are single-peaked there, and their arena median ratio is 2.9 (P) and 3.5 (PA), near but above the paper's 1.5 to 2. HP and HPA units sit with the head-direction ones (arena ratios 8.9 and 4.7). Only the place-derived units behave like the recorded cells off the track. Under a strict recount requiring an arena ratio below 2, every input set yields under 0.5 axis units per trained network.

**6. Anchoring (Fig. 5, right polar plots; rotation notebook figure 03).** With the track turned 90° clockwise and the place fields held fixed in the room, head-direction GRU axis units keep their room direction: median room-frame r 0.78 against track-frame r −0.36, close to the paper's 0.76 and −0.41; 99% of units room-anchored, 10 of 10 networks mostly so; but only 11 of 71 still pass the two-peak rule when turned, so the direction survives and the shape mostly does not. Place-only units neither stay nor turn: 29% room-anchored, median track-frame r 0.09, and none of their 17 axis units passes when turned. The mixed arms sit between: HP 73% and hidden 256 65% room-anchored, with room-frame r 0.42 and 0.28. At 45° the ordering is the same (H 0.86, HP 0.79, hidden 256 0.59, P 0.59 room-anchored). Room anchoring follows the heading input, not the task.

## 9. The two discriminating tests: arena and rotation

The criterion alone cannot tell a genuine axis code from a head-direction cell folded by the corridors: on a corridor the animal faces the way it travels, so a unit tuned to one heading has a travel peak there, and the opposite peak comes from the same cell's broad tuning plus the restricted headings the corridor allows. The paper's own evidence against this reading is the arena, where a head-direction cell keeps a single sharp peak and an axis cell goes flat. Two tests were therefore added, both model independent and both applicable to recorded cells.

**The arena contrast** (criterion notebook): for every axis unit, the track ratio and arena ratio, and the per-peak widths from the paper's mixture fit, compared pairwise, with the network as the unit of analysis. Outcome in result 5: head-direction units are head-direction cells (sharper in the arena than on the track); place units go the paper's way in direction (broader, single-peaked, weaker) though not all the way in level.

**The rotation test** (experiment 2026-10-29): the test blocks are turned about the room centre by 45° and 90°, heading turned with them, place fields left in room coordinates, the network re-run, and each axis unit's turned tuning correlated with its original in the room frame and in the track frame. A heading readout must be room-anchored. A unit built from the sequence of place fields along a corridor should turn with the track if the sequence survives, or lose its tuning if it does not. Outcome in result 6: heading units match the paper's cells quantitatively; place units lose their tuning rather than turning it, because moving the track across fixed fields breaks the sequence; mixed arms are mostly heading readouts with a place-driven minority.

Together: the paper's cells are room-anchored *and* lose their arena tuning. No model unit does both. Heading units are room-anchored but sharp in the arena; place units broaden in the arena but are not room-anchored. That is the honest summary, and the discussion's hex-maze proposal is the planned way to break the tie.

## 10. Discussion points and likely questions

**The task and the track may both be too easy.** With place input, predicting position 1 s ahead on fixed routes is nearly solved (fit 0.16 to 0.22), and adding head direction or angular velocity barely moves it. The triple-T has corridors in only two orientations, so a heading-tuned unit folds into opposite peaks by geometry. A hex maze, with corridors at three orientations 60° apart, separates the accounts: a unit inheriting head-direction tuning should fire on the two or three corridor directions within its tuning width, while a genuine axis code keeps two peaks 180° apart at one of the three orientations. Hex-maze trajectory data and task training are being incorporated in follow-up work.

**What the arena criterion could ask.** The ported release is the paper's formal test and it lets head-direction cells through. Options discussed in the criterion note: keep the paper's criterion as the headline and report the contrast beside it (chosen for the poster), or add an arena modulation bound in a new validator version (deferred; the value would be arbitrary and most claims would not survive a bound of 2, which is itself a finding to show rather than hide).

**Other learning rules.** Local, unsupervised rules (Hebbian, Oja) and reinforcement learning are the natural next step; the rule that forms the code may itself be the explanation of why the code is axial rather than directional. A Hebbian arm was deferred by decision before the poster.

**Likely questions.**

- *Why only 10 seeds per arm?* Ten seeds against 100 draws gives a permutation test with a floor of 1e-5 and enough power to detect shifts of one unit per network (the place claims have CIs of about ±0.8). The sweep design has 440 trainings in total; fresh seeds are the proposed confirmation for the two small GRU claims (HP, history 1 s).
- *Why does the GRU differ from the step RNN?* Not resolved. Observations: the step RNN with head and place input loses axis-shaped units relative to its null in 16 of 16 arms, the GRU scatters around chance; GRU hidden states are clipped at 0 for scoring, which is a provisional rate rule the step RNN does not need. Say that the cell-type dependence is a result to explain, not an explanation.
- *Aren't the head-direction units just head-direction cells?* Yes, in the arena and under rotation they behave as such. That is result 5 and 6, stated on the poster. They are counted because the paper's formal criterion counts them; the contrast is what separates them.
- *Why 10° bins?* The previous repository's validator used 36 bins and the port keeps it so that every stored result is comparable; the paper's bin width is not reproduced here. Widths are therefore compared by direction, not level.
- *Why are your peaks broader than the paper's?* 10° bins, the κ cap at 50, an order-2 fit forced on the arena curve, and rates without spike noise all broaden the fitted components. Ratios are in the paper's range; variances are about twice.
- *Is 1.7 axis units per network meaningful?* It is 1.1% of 128 hidden units, against 0.3 by chance, consistent across seeds (5 or 6 of 10 networks above the null's 95th percentile) and robust to leaving out any seed. It is small, and the poster says so; the point is that it comes with the paper's arena behaviour, which the many head-direction units do not.
- *Why does the full model sit below chance?* Untrained networks with head-direction input already hold 3 to 4 axis-shaped units; training on position prediction removes some of them. In the step RNN the loss is already at the shape rule (fewer axis-shaped curves after training). Whether this is a real effect of training or an interaction between the validator's rules and trained activity statistics (sparser, lower-variance units failing the shape fit) is open; it was a post hoc reading and would need fresh seeds against a stated prediction.
- *Did the H networks learn anything?* Unknown against a baseline they could reach. The persistence baseline uses the current position, which they never receive; a mean-position baseline was proposed and not run.
- *How were the six example units chosen?* By hand from the pool of 998 trained axis units, to span five kinds (room anchored, sharp bimodal, corridor-wide, diagonal, head direction only) across cell types, inputs and seeds. Say "chosen to span the range", not "sampled".
- *What about the kind labels?* Not used; see section 5.
- *Multiple comparisons?* 44 tests at 0.01, about 0.44 false claims expected under the global null, every test shown.

## 11. Glossary

- **Arm.** One experimental condition: an input set or one sweep value, run in both cell types with 10 seeds.
- **Arm test.** The one-sided permutation Mann-Whitney test of an arm's 10 trained counts against the 100 untrained draws of its null set; a claim when p < 0.01.
- **Axis shape.** A tuning curve whose chosen von Mises mixture has order 2, opposite peaks within 20°, peak data ≥ 0.1 and peak over trough > 2.
- **Axis unit.** A hidden unit with an axis shape on the track, spatial independence at both peaks, and no axis shape in the arena. The headline count.
- **Arena release.** The rule that the arena head-direction curve must fail the axis shape test.
- **Chance class.** Zero, rare or expected: whether untrained networks of a set hold no, under 0.5, or more axis units per network on average.
- **Circular variance / circular standard deviation.** The spread of a von Mises component: 1/κ in the paper's units, sqrt(−2 ln(I₁(κ)/I₀(κ))) in degrees in ours.
- **Fit ratio.** Best validation loss of a network divided by the persistence loss on the same windows; below 1 beats persistence.
- **Head direction, travel direction.** The direction the head points versus the direction the position is moving; equal in corridors, divergent at turns, pauses and in the arena.
- **Null set.** 100 untrained networks of one cell type, hidden size and input set, scored by the validator.
- **Peak-to-trough ratio.** The mean of the tuning curve at the fitted model's peak bins over its trough bins.
- **Permutation p.** The fraction of random relabellings of the pooled counts giving a rank sum at least as extreme as the observed, plus one in numerator and denominator.
- **Persistence.** The prediction that the future position equals the current one.
- **pmf.** Probability mass function: the fitted probability of each integer count.
- **Room frame, track frame.** Reading a turned tuning curve in room coordinates, or turned back by the rotation angle into the track's coordinates.
- **Spatial independence.** The fraction of 2 cm position bins traversed in a peak direction in which the unit is at least half its mean activity.
- **Step RNN.** The poster's "vanilla RNN": a hand-stepped recurrent network with a rectified tanh nonlinearity.
- **Triple-T.** The maze: a start corridor and three successive T junctions leading to four reward arms, with perimeter return corridors.
- **von Mises mixture.** The paper's tuning-curve model: a sum of circular bell curves fitted by EM.
