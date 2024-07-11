package com.example.test;

import java.util.*;
import java.util.concurrent.Callable;
import java.util.function.Function;
import java.io.Serializable;

// Top-level annotation
@SuppressWarnings("unused")
// Generic type declaration
public class TestClass<T extends Comparable<T> & Serializable> implements Runnable {

    // Static nested class
    public static class NestedClass {
        private int nestedField;
    }

    // Inner class
    public class InnerClass {
        public void innerMethod() {
            System.out.println(outerField);
        }
    }

    // Enum declaration
    public enum Color {
        RED, GREEN, BLUE;
        
        public String getDescription() {
            return name().toLowerCase();
        }
    }

    // Interface declaration
    public interface TestInterface {
        void interfaceMethod();
        
        // Default method
        default void defaultMethod() {
            System.out.println("Default implementation");
        }
    }

    // Annotation declaration
    public @interface TestAnnotation {
        String value() default "default";
        int count();
    }

    // Static initializer
    static {
        System.out.println("Static initializer");
    }

    // Instance initializer
    {
        System.out.println("Instance initializer");
    }

    // Fields
    private final int finalField = 10;
    public static String staticField = "Static";
    protected T genericField;
    volatile boolean volatileField;
    transient long transientField;

    // Constructor
    public TestClass(T genericParam) {
        this.genericField = genericParam;
    }

    // Method with generic type
    public <U extends Number> U genericMethod(U param) {
        return param;
    }

    // Varargs method
    public void varargsMethod(String... args) {
        for (String arg : args) {
            System.out.println(arg);
        }
    }

    // Synchronized method
    public synchronized void synchronizedMethod() {
        // Synchronized block
        synchronized (this) {
            System.out.println("Synchronized block");
        }
    }

    // Method with throws clause
    public void exceptionMethod() throws Exception {
        throw new Exception("Test exception");
    }

    // Overridden method
    @Override
    public void run() {
        System.out.println("Running");
    }

    // Lambda expression
    private Runnable lambdaField = () -> System.out.println("Lambda");

    // Method reference
    private Function<String, Integer> methodRef = String::length;

    // Try-with-resources
    public void tryWithResources() {
        try (Scanner scanner = new Scanner(System.in)) {
            System.out.println(scanner.nextLine());
        }
    }

    // Anonymous inner class
    private Callable<Integer> anonymousClass = new Callable<Integer>() {
        @Override
        public Integer call() throws Exception {
            return 42;
        }
    };

    // Static method
    public static void staticMethod() {
        System.out.println("Static method");
    }

    // Main method
    public static void main(String[] args) {
        TestClass<String> instance = new TestClass<>("Test");
        instance.run();
    }

    // Private method
    private void privateMethod() {
        // Local class
        class LocalClass {
            void localMethod() {
                System.out.println("Local method");
            }
        }
        new LocalClass().localMethod();
    }

    // Getter and Setter
    private int outerField;
    public int getOuterField() {
        return outerField;
    }
    public void setOuterField(int outerField) {
        this.outerField = outerField;
    }
}

// Another top-level class (non-public)
class AnotherClass implements TestClass.TestInterface {
    @Override
    public void interfaceMethod() {
        System.out.println("Implemented interface method");
    }
}

// Record (Java 14+)
record Point(int x, int y) {
    // Compact constructor
    public Point {
        if (x < 0 || y < 0) {
            throw new IllegalArgumentException("Coordinates cannot be negative");
        }
    }
}

// Sealed class (Java 15+)
sealed class Shape permits Circle, Square {
    // ...
}

final class Circle extends Shape {
    // ...
}

non-sealed class Square extends Shape {
    // ...
}