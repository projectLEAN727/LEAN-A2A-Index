// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IVerifier {
    function verifyProof(
        bytes calldata proof,
        uint256[3] calldata publicInputs
    ) external view returns (bool);
}

contract FluidControlOracle {
    address public verifier;
    address public owner;
    
    // Protocol Fee (Auto-Tax & Fee Switch)
    address payable public treasuryAddress;
    uint256 public feeBps; // Fee in Basis Points (e.g., 250 = 2.5%, default 0)

    event ControlUnlocked(
        bytes32 indexed instance_id,
        bytes32 indexed payment_tx_hash,
        string gcode_uri
    );

    event PaymentProcessed(
        bytes32 indexed payload_id,
        address indexed buyer,
        address indexed seller,
        uint256 total_amount,
        uint256 fee_amount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Caller is not the owner");
        _;
    }
    
    constructor(address _verifier, address payable _treasuryAddress) {
        require(_verifier != address(0), "Invalid verifier address");
        verifier = _verifier;
        owner = msg.sender;
        treasuryAddress = _treasuryAddress;
        feeBps = 0; // Initial Fee Switch set to 0
    }

    function setFeeBps(uint256 _feeBps) external onlyOwner {
        require(_feeBps <= 10000, "Fee BPS cannot exceed 100%");
        feeBps = _feeBps;
    }

    function setTreasuryAddress(address payable _treasuryAddress) external onlyOwner {
        require(_treasuryAddress != address(0), "Invalid treasury address");
        treasuryAddress = _treasuryAddress;
    }

    /**
     * @notice Mediates payload settlement between buyer and seller with optional Protocol Fee split.
     * @param payload_id The unique bytes32 identifier of the requested payload.
     * @param seller The recipient wallet address of the seller node.
     */
    function payAndUnlock(bytes32 payload_id, address payable seller) external payable returns (bool success) {
        require(msg.value > 0, "Payment required");
        require(seller != address(0), "Invalid seller address");

        uint256 feeAmount = (msg.value * feeBps) / 10000;
        uint256 sellerAmount = msg.value - feeAmount;

        if (feeAmount > 0 && treasuryAddress != address(0)) {
            (bool feeSent, ) = treasuryAddress.call{value: feeAmount}("");
            require(feeSent, "Failed to send fee to treasury");
        }

        (bool sellerSent, ) = seller.call{value: sellerAmount}("");
        require(sellerSent, "Failed to send payment to seller");

        emit PaymentProcessed(payload_id, msg.sender, seller, msg.value, feeAmount);
        return true;
    }
    
    function submitControlProof(
        bytes memory proof,
        bytes32 fluid_viscosity_hash,
        bytes32 boundary_condition_hash,
        bytes32 control_field_hash,
        bytes32 payment_tx_hash
    ) public returns (bool success) {
        uint256[3] memory publicInputs = [
            uint256(fluid_viscosity_hash),
            uint256(boundary_condition_hash),
            uint256(control_field_hash)
        ];
        
        bool verified = IVerifier(verifier).verifyProof(proof, publicInputs);
        require(verified, "Invalid ZK proof");
        
        bytes32 instance_id = keccak256(abi.encodePacked(
            fluid_viscosity_hash,
            boundary_condition_hash,
            control_field_hash,
            block.timestamp
        ));
        
        string memory mock_gcode_uri = "QmLEANMasterColdLightChipActiveGCodePayloadURI";
        
        emit ControlUnlocked(instance_id, payment_tx_hash, mock_gcode_uri);
        return true;
    }
}
