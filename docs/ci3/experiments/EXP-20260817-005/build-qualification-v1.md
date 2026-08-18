# EXP-20260817-005 build qualification v1

**Verdict: SELECTED LEGAL FIXTURE BUILD PASS; FULL UPSTREAM SUITE TOOLCHAIN-BLOCKED**

- Pinned source: `dolphin-emu/hwtests@f28077b139eec18967f60db6ce1e15b182dfeac0`
- Recorded toolchain digest: `devkitpro/devkitppc@sha256:44cb1a920e1ec3ec7c06767493c3b85f8d643d6137cc4661f0201895ac6e4967`
- Pre-registered selected targets built: 20
- Required executable outputs verified: 20
- Raw selected-build log SHA-256: `7fd56b92ccc75b7ac21a0b6ebec0cba564c3f7496fdf3665191f938c3ac0cc91`
- Successful workflow run: `32110199577`

The selected set consists of register/CPU and GX workloads chosen from source classes before any profiler, coverage, or performance output was available.

| Target | Output | Size (bytes) | SHA-256 |
|---|---|---:|---|
| `cputest_cr` | `build/cputest/cputest_cr.elf` | 3776656 | `a6ad00f9399816530cb95e6fb659030ba51a5748c3abc5f3163cb50abd14d95b` |
| `cputest_fctiw` | `build/cputest/cputest_fctiw.elf` | 3819612 | `891d57de97240c078205836a76675f0dc02d312992a40b456191da4723766365` |
| `cputest_fctiwz` | `build/cputest/cputest_fctiwz.elf` | 3772656 | `64c5bfcddc19c9ffc6572b65787829e7685a746a498eafde45997c7add44f1e1` |
| `cputest_frsp` | `build/cputest/cputest_frsp.elf` | 3774596 | `d6a6f6c9852b39c6cb33cb44fc0115be776ead9ce9abcf3d835f5872985c936a` |
| `cputest_fprf` | `build/cputest/cputest_fprf.elf` | 3808892 | `cf27d1fa6f4f4dc20405a8a64d3e3b41b17d00f59dd16aa3c39f8d02add61f99` |
| `cputest_load` | `build/cputest/cputest_load.elf` | 3233404 | `0647e3e92f3504806ee73a25b4b35b35b64424b41617504577719e4ec9f65af2` |
| `cputest_mtspr` | `build/cputest/cputest_mtspr.elf` | 3771824 | `32d40f003954a063fc940bc3f15b989ac8a349801caff84fd1dfc01ba5271f19` |
| `cputest_nan` | `build/cputest/cputest_nan.elf` | 3919468 | `44d9b67922e49292b9d92158433a7f816a5c0d3063f240b6b28faf419605e0bc` |
| `cputest_ni` | `build/cputest/cputest_ni.elf` | 3795304 | `9c7d1d0d8a7f59e576cfd114ec18ff7a66ddc9aac8501b8a59c235b0da4bd1f0` |
| `cputest_pairedmove` | `build/cputest/cputest_pairedmove.elf` | 3862316 | `a13a6dc406f92aecabbf585036d1d05e8506481bd4e9e4ce67c3a71777bbc078` |
| `cputest_reciprocal` | `build/cputest/cputest_reciprocal.elf` | 3816144 | `ac94372be2536307a71f68b7418324989683c1802d6a5115ffaf14c631fc0f03` |
| `cputest_rlw` | `build/cputest/cputest_rlw.elf` | 3246136 | `2d3904ade2eb089d7b3e250d547ebeff5623485f0d74fcb6128023bf3e63cafd` |
| `cputest_srawix` | `build/cputest/cputest_srawix.elf` | 3841200 | `a53518ba3009d92917ced8bf55040185d5f9fe88254e59f02c9588880e82a000` |
| `gxtest_bitfield` | `build/gxtest/gxtest_bitfield.elf` | 4152732 | `ea79ed906a47a9c2f7b181c4ba30aba70633d484ddd4582f0098e247c6507e24` |
| `gxtest_clipping` | `build/gxtest/gxtest_clipping.elf` | 4032944 | `142a84edb69bf81b68abb1fea2e8af2b97109857d460ad77d539a6d56bd807c3` |
| `gxtest_copyfilter` | `build/gxtest/gxtest_copyfilter.elf` | 4685652 | `2f6edbe8fd3854cad29d968326a335c2cdacb7a5e37e3ff39d27159be8c3030e` |
| `gxtest_intensity` | `build/gxtest/gxtest_intensity.elf` | 4026920 | `1ab9f2f3090b82e4b07dc7e26bd071956c3514cedc62cb083652727710b60f77` |
| `gxtest_lighting` | `build/gxtest/gxtest_lighting.elf` | 4061748 | `c9f2c1fc33a0d673c84bfb58ab293d04aa41125251b2a2ba0ebbd6de25e547d4` |
| `gxtest_rasterization` | `build/gxtest/gxtest_rasterization.elf` | 4031260 | `ffefa28528ca21fc55f76c4309610e000104b19ec6ab375cc4e9918072482310` |
| `gxtest_tev` | `build/gxtest/gxtest_tev.elf` | 4742324 | `ebcd0322c542bc606ffc69726992794b79e3929cb1d577fa13f9bddb7d5b4fee` |

## Recorded full-suite blocker

A prior attempt to build every pinned upstream target under the same current toolchain failed only after the selected CPU/GX targets had begun building. The current libogc `ogc/ipc.h` macro `HW_IPC_PPCMSG` collides with the pinned `iostest/ipc.cpp` enum member of the same name. The pinned source was not patched. Full-suite qualification therefore remains false; workflow run `32108796444` and diagnostic artifact `9314124919` preserve the exact failure.

## Interpretation boundary

- This proves only that the explicit selected legal fixture set builds in the recorded toolchain.
- It does not claim that every upstream hwtests target builds.
- No fixture has been launched or shown deterministic.
- No profiler environment variable was set.
- No schema-v1 profile was generated or examined.
- Build success is not route qualification, workload representativeness, coverage, overhead, lowering correctness, or performance evidence.

The next step is non-profiled route qualification of this selected set. Exact runtime fixtures must still be frozen before profile output is opened.
