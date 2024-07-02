#include <iostream>
#include <vector>
#include <memory>
#include <functional>

// Forward declaration
class ForwardDeclared;

// Namespace
namespace TestNamespace {

// Enum class
enum class Color { Red, Green, Blue };

// Template function declaration
template<typename T>
void printValue(T value);

// Class definition with various features
class TestClass {
public:
    // Constructor
    TestClass() = default;
    
    // Virtual destructor
    virtual ~TestClass() = 0;
    
    // Pure virtual function
    virtual void pureVirtualFunc() = 0;
    
    // Static member
    static int staticMember;
    
    // Const member function
    void constMemberFunc() const;
    
    // Template member function
    template<typename T>
    T templateMemberFunc(T arg);
    
private:
    int privateVar;
    
protected:
    double protectedVar;
};

// Struct definition
struct TestStruct {
    int x;
    double y;
};

// Union definition
union TestUnion {
    int intValue;
    float floatValue;
};

// Function with multiple parameters and default argument
void multiParamFunc(int a, double b, std::string c = "default");

// Lambda function
auto lambdaFunc = [](int x, int y) -> int { return x + y; };

// Template class
template<typename T, typename U>
class TemplateClass {
public:
    T tValue;
    U uValue;
};

// Typedef and using declaration
typedef std::vector<int> IntVector;
using DoubleVector = std::vector<double>;

// Function pointer typedef
typedef void (*FuncPtr)(int);

// Variadic template
template<typename... Args>
void variadicFunc(Args... args);

// Constexpr function
constexpr int constexprFunc(int x) { return x * 2; }

// Inline namespace
inline namespace InlineNS {
    void inlineNamespaceFunc();
}

// Friend function declaration
class FriendClass {
    friend void friendFunc(FriendClass&);
};

// Nested class
class OuterClass {
    class InnerClass {
        // ...
    };
};

// Anonymous namespace
namespace {
    void anonymousFunc() {
        // ...
    }
}

// Function with trailing return type
auto trailingReturnFunc() -> int;

// Operator overloading
struct OverloadedOp {
    bool operator==(const OverloadedOp& other) const;
};

// Attributes
[[deprecated("Use newFunc instead")]]
void oldFunc();


// // Concepts (C++20)
// template<typename T>
// concept Printable = requires(T t) {
//     { std::cout << t } -> std::same_as<std::ostream&>;
// };

// // Coroutine (C++20)
// #include <coroutine>
// std::generator<int> generateNumbers();

// } // namespace TestNamespace

// Global variable
int globalVar = 42;

// Main function
int main() {
    // Local variable
    int localVar = 10;
    
    // Function call
    TestNamespace::multiParamFunc(1, 2.0);
    
    // Template instantiation
    TestNamespace::TemplateClass<int, double> tc;
    
    return 0;
}