CXX = g++
CXXFLAGS = -O3 -Wall -shared -static -static-libgcc -static-libstdc++
LDFLAGS = -lpsapi

TARGET = mem_reduct.dll

all: $(TARGET)

$(TARGET): mem_reduct.cpp mem_reduct.h
	$(CXX) $(CXXFLAGS) -o $(TARGET) mem_reduct.cpp $(LDFLAGS)

clean:
	rm -f $(TARGET)
