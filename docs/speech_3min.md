# Three-minute poster walk

Spoken, first person, about 420 words. Cues in brackets. Numbers from the arm tables of experiments 2026-10-24 and 2026-10-25, the claims table of 2026-10-28, the criterion note of results/sfn-2026/sfn_2026_criterion and the rotation table of 2026-10-29, all under the permutation arm test of 2026-11-09.

---

Thanks for stopping. This poster is about a cell type in the subiculum called the axis-tuned cell. Olson, Tongprasearth and Nitz found them in 2017 in rats running a triple-T maze [point to Fig. 1]: a cell fires when the animal travels north or south along a corridor, in either direction, wherever that corridor is in the room. Two opposite peaks, no place field, and the tuning goes away in an open arena, so it is not a head-direction cell.

Our question is whether that code can emerge on its own inside a latent-variable model trained on the rat's own trajectories, with no instruction to be direction tuned.

Here is the method [point to Fig. 2]. We take 81 sessions from three rats on the same maze and arena, turn them into clean 20 Hz blocks, and train small recurrent networks, a step RNN and a GRU, to predict the animal's position one second ahead from populations of head-direction cells, place cells and angular-velocity cells. Every hidden unit is scored by the paper's own criterion, and each trained network is compared with 100 untrained networks of the same type and inputs [point to Fig. 3], because untrained networks already contain a few units that pass.

Three findings.

First [point to Fig. 4, blue]: head-direction input alone gives the most axis-shaped units, about seven per network against under two by chance, but those networks never learn the task. And when we look in the arena [point to Fig. 5, grey curves], they are sharper there than on the track, tuned to heading rather than to an axis, and when we turn the track ninety degrees [point to the purple polar plots] they stay locked to the room, exactly as the recorded cells did. So they are head-direction cells that the corridor folds into two peaks.

Second [point to Fig. 4, green]: place input alone learns the task and produces one to two axis units per network above chance. Those are the units that behave like the paper's cells off the track: their tuning broadens in the arena, and turning the track destroys it rather than moving it.

Third [point to Fig. 6]: the full model, with all three inputs, sits at or below chance in both architectures. Adding head direction to place barely changes the fit and adds no axis units beyond what chance already gives. We think the task and the track are too easy: corridors run in two orientations, so a heading-tuned unit already looks axis tuned.

Our next step is a hex maze [point to Discussion], where corridors run at three orientations sixty degrees apart. There a heading readout and a genuine axis code make different predictions, so the geometry does the discriminating for us.

The short version: the inputs set the chance level, place input gives a few real ones, and the arena and the rotation test tell the two apart. Happy to go into any panel.

---

## Thirty-second version

Olson and Nitz found subicular cells tuned to the axis of travel, two opposite peaks, no place field. We asked whether such units emerge in recurrent networks trained to predict a rat's position from its own trajectories. Head-direction input alone yields many axis-shaped units, but they are head-direction cells in disguise: sharp in the arena and room-anchored under rotation. Place input yields a few that behave like the recorded cells. The full model sits at chance. Next: a hex maze, where the geometry separates the two.
