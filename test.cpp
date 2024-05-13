#include <iostream>

template<typename T, int PRR = 0>
void test(T t) {
    if constexpr (PRR == 1) {
        std::cout << "EF" << std::endl;
    } else if constexpr (PRR == 2) {
        std::cout << "DAC" << std::endl;
    } else {
        std::cout << "default" << std::endl;
    }
}

int main() {
    test<int, 0>(0);
    test<int>(0);
    test<int, 1>(0);
    test<int, 2>(0);
    return 0;
}