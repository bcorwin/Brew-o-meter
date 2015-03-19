int light = A1;
int temp_amb = A0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  int light_val = analogRead(light);
  float temp_amb_val = 1.8*(analogRead(temp_amb)*4960.0/1024.0 - 500.0)/10.0 + 32.0;
  float chk_sum = light_val + temp_amb;

  Serial.print("{");
  
  Serial.print("'chk_sum':");
  Serial.print(chk_sum);
  
  Serial.print(", 'light_amb':");
  Serial.print(light_val);
  
  Serial.print(", 'temp_amb':");
  Serial.print(temp_amb_val);
  
  Serial.print("}\n");
  delay(500);
}
