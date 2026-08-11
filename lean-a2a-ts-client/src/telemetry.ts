export interface StepLatencies {
  [stepName: string]: number;
}

export interface TelemetryData {
  timestamp: number;
  scenario: string;
  payload_id: string;
  total_latency_ms: number;
  latencies_ms: StepLatencies;
  gas_used_mnt: string;
  payment_amount_mnt: number;
  treasury_fee_mnt: number;
  status: string;
  error_message?: string;
}

export class TelemetryMetrics {
  public scenarioName: string;
  public payloadId: string;
  public startTime: number;
  public endTime: number | null = null;
  public stepStarts: Record<string, number> = {};
  public stepLatencies: Record<string, number> = {};
  public gasUsedMnt: string = '0';
  public paymentAmountMnt: number = 0;
  public treasuryFeeMnt: number = 0;
  public status: string = 'IN_PROGRESS';
  public errorMessage?: string;

  constructor(scenarioName: string, payloadId: string) {
    this.scenarioName = scenarioName;
    this.payloadId = payloadId;
    this.startTime = Date.now();
  }

  public startStep(stepName: string): void {
    this.stepStarts[stepName] = Date.now();
  }

  public endStep(stepName: string): void {
    if (this.stepStarts[stepName]) {
      const latency = Date.now() - this.stepStarts[stepName];
      this.stepLatencies[stepName] = Number(latency.toFixed(2));
    }
  }

  public setOnchainMetrics(gasUsedMnt: number, paymentAmountMnt: number, treasuryFeeMnt: number): void {
    this.gasUsedMnt = gasUsedMnt.toFixed(6);
    this.paymentAmountMnt = paymentAmountMnt;
    this.treasuryFeeMnt = treasuryFeeMnt;
  }

  public finish(status: string = 'SUCCESS', errorMessage?: string): void {
    this.endTime = Date.now();
    this.status = status;
    this.errorMessage = errorMessage;
  }

  public toObject(): TelemetryData {
    const totalLatency = (this.endTime || Date.now()) - this.startTime;
    const data: TelemetryData = {
      timestamp: Math.floor(this.startTime / 1000),
      scenario: this.scenarioName,
      payload_id: this.payloadId,
      total_latency_ms: Number(totalLatency.toFixed(2)),
      latencies_ms: this.stepLatencies,
      gas_used_mnt: this.gasUsedMnt,
      payment_amount_mnt: this.paymentAmountMnt,
      treasury_fee_mnt: this.treasuryFeeMnt,
      status: this.status
    };
    if (this.errorMessage) {
      data.error_message = this.errorMessage;
    }
    return data;
  }

  public toJson(): string {
    return JSON.stringify(this.toObject(), null, 2);
  }
}

export class TelemetryLogger {
  private currentMetrics: TelemetryMetrics | null = null;

  public startScenario(scenarioName: string, payloadId: string): TelemetryMetrics {
    this.currentMetrics = new TelemetryMetrics(scenarioName, payloadId);
    return this.currentMetrics;
  }

  public getMetrics(): TelemetryMetrics | null {
    return this.currentMetrics;
  }
}

export const globalTelemetry = new TelemetryLogger();
