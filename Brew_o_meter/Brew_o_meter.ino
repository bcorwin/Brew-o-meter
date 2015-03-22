int light = A1;
int temp_amb = A0;
int temp_beer = A2;
int pres_beer = A3;

void setup() {
  Serial.begin(9600);
}

void loop() {
  int req = Serial.read();
  if(req == 82) {    
    float light_val = analogRead(light);
    float temp_amb_val = 1.8*(analogRead(temp_amb)*4960.0/1024.0 - 496.0)/10.0 + 32.0;
    float temp_beer_val = 1.8*(analogRead(temp_beer)*4960.0/1024.0 - 496.0)/10.0 + 32.0;
    float pres_beer_val = analogRead(pres_beer);
    
    float chk_sum = light_val + temp_amb_val + temp_beer_val + pres_beer_val;
    
    Serial.print("{");
    
    Serial.print("'chk_sum':");
    Serial.print(chk_sum);
    
    Serial.print(", 'light_amb':");
    Serial.print(light_val);
    
    Serial.print(", 'temp_amb':");
    Serial.print(temp_amb_val);
    
    Serial.print(", 'temp_beer':");
    Serial.print(temp_beer_val);
    
    Serial.print(", 'pres_beer':");
    Serial.print(pres_beer_val);
    
    Serial.println("}");
  } else if(req == 69) {
    Serial.println("Established");
  }
}
