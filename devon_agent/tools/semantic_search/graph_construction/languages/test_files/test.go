package main

import (
	"fmt"
	"sync"
	"time"
)

// Constant declarations
const (
	Pi        = 3.14159
	MaxRetries = 3
	
)

// Variable declarations
var (
	globalVar1 int
	globalVar2 string = "global"
)

// Interface declaration
type Printer interface {
	Print() string
}

// Struct declaration
type Person struct {
	Name string
	Age  int
}

// Method declaration
func (p Person) Print() string {
	return fmt.Sprintf("%s is %d years old", p.Name, p.Age)
}

// Function declaration
func add(a, b int) int {
	return a + b
}

// Function with multiple return values
func divideAndRemainder(a, b int) (int, int, error) {
	if b == 0 {
		return 0, 0, fmt.Errorf("division by zero")
	}
	return a / b, a % b, nil
}

// Function with named return values
func rectangleProps(width, height float64) (area, perimeter float64) {
	area = width * height
	perimeter = 2 * (width + height)
	return
}

// Struct with embedded type
type Employee struct {
	Person
	Title string
}

// Interface with embedded interface
type AdvancedPrinter interface {
	Printer
	PrintJSON() string
}

// Type alias
type Celsius = float64

// Type definition
type Fahrenheit float64

// Method on type definition
func (f Fahrenheit) ToCelsius() Celsius {
	return Celsius((f - 32) * 5 / 9)
}

// Iota enum-like constants
const (
	Sunday = iota
	Monday
	Tuesday
	Wednesday
	Thursday
	Friday
	Saturday
)

// Function with variadic parameters
func sum(nums ...int) int {
	total := 0
	for _, num := range nums {
		total += num
	}
	return total
}

// Function with defer
func deferExample() {
	defer fmt.Println("This will be printed last")
	fmt.Println("This will be printed first")
}

// Goroutine and channel example
func channelExample() {
	ch := make(chan int, 2)
	go func() {
		ch <- 1
		ch <- 2
		close(ch)
	}()
	for num := range ch {
		fmt.Println(num)
	}
}

// Struct with tags
type TaggedStruct struct {
	Field1 string `json:"field_1"`
	Field2 int    `json:"field_2,omitempty"`
}

// Interface with generic type parameter
type Comparer[T any] interface {
	Compare(T) int
}

// Generic function
func PrintSlice[T any](s []T) {
	for _, v := range s {
		fmt.Println(v)
	}
}

// Struct with generic type parameter
type Stack[T any] struct {
	items []T
}

func (s *Stack[T]) Push(item T) {
	s.items = append(s.items, item)
}

// Main function
func main() {
	person := Person{Name: "Alice", Age: 30}
	fmt.Println(person.Print())

	result := add(5, 3)
	fmt.Printf("5 + 3 = %d\n", result)

	quotient, remainder, err := divideAndRemainder(10, 3)
	if err == nil {
		fmt.Printf("10 / 3 = %d remainder %d\n", quotient, remainder)
	}

	area, perimeter := rectangleProps(5, 3)
	fmt.Printf("Rectangle area: %.2f, perimeter: %.2f\n", area, perimeter)

	deferExample()

	channelExample()

	temp := Fahrenheit(98.6)
	fmt.Printf("%.2f°F is %.2f°C\n", temp, temp.ToCelsius())

	fmt.Printf("Sum of 1, 2, 3: %d\n", sum(1, 2, 3))

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		fmt.Println("This is running in a goroutine")
	}()
	wg.Wait()

	PrintSlice([]string{"Go", "is", "awesome"})

	stack := Stack[int]{}
	stack.Push(1)
	stack.Push(2)
	stack.Push(3)
}