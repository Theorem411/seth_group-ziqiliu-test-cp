constexpr int max_value = 255;
using value = unsigned char; 
using row = parlay::sequence<value>;
/** PRR: */
using AllocatorTy = parlay::internal::sequence_default_allocator<value>;
constexpr bool EnableSSO = std::is_same<value, char>::value;
using row_ef = parlay::sequence<value, AllocatorTy, EnableSSO, 1>;
using row_dac = parlay::sequence<value, AllocatorTy, EnableSSO, 2>;
///////////
using rows = parlay::sequence<row>;
/** PRR: */
using rows_ef = parlay::sequence<row_ef>;
using rows_dac = parlay::sequence<row_dac>;
///////////

struct feature {
  bool discrete; // discrete (true) or continuous (false)
  int num;       // max value of feature
  row vals;      // the sequence of values for the feature
  feature(bool discrete, int num) : discrete(discrete), num(num) {}
  feature(bool d, int n, row v) : discrete(d), num(n), vals(v) {}
};

using features = parlay::sequence<feature>;

row_ef classify(features const &Train, rows const &Test, bool verbose);
