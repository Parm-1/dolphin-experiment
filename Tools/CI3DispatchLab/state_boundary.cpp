#include "state_model.h"

#include <atomic>

#if defined(__GNUC__) || defined(__clang__)
#define CI3_NOINLINE __attribute__((noinline))
#else
#define CI3_NOINLINE
#endif

extern "C" CI3_NOINLINE void CI3SemanticBoundary(CI3StateModel* state) noexcept
{
#if defined(__GNUC__) || defined(__clang__)
  asm volatile("" : "+m"(state->regs[0]), "+m"(state->regs[1]), "+m"(state->regs[2]),
               "+m"(state->regs[3])
               :
               : "memory");
#else
  (void)state;
  std::atomic_signal_fence(std::memory_order_seq_cst);
#endif
}
